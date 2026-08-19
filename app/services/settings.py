"""应用设置（JSON 持久化到 %APPDATA%/NetPulse）。"""
import json
import os
import time


class AppSettings:
    DEFAULTS = {
        "theme": "light",             # dark / light
        "language": "auto",            # auto（跟随系统）/ zh-CN / en-US
        "default_threads": 8,
        "default_timeout_ms": 5000,
        "default_rate": 100,
        "default_duration": 30,
        "default_packet_size": 64,
        "log_dir": "",                # 空则使用默认目录
        "disclaimer_accepted": False,
        "authorized": [],             # [{host, note, ts}]
        "stress_form": {},            # 上次压测表单：{target, port, protocol, threads, rate, dur, dur_unit}
        "minimize_to_tray": True,     # 关闭时最小化到托盘
    }

    def __init__(self):
        root = os.environ.get("APPDATA", os.path.expanduser("~"))
        base = os.path.join(root, "NetPulse")
        old = os.path.join(root, "NetPulsePy", "settings.json")
        # 一次性迁移：旧版（NetPulsePy）配置复制到新目录
        if not os.path.exists(os.path.join(base, "settings.json")) and os.path.exists(old):
            try:
                os.makedirs(base, exist_ok=True)
                with open(old, "r", encoding="utf-8") as f:
                    data = f.read()
                with open(os.path.join(base, "settings.json"), "w", encoding="utf-8") as f:
                    f.write(data)
            except Exception:
                pass
        os.makedirs(base, exist_ok=True)
        self.path = os.path.join(base, "settings.json")
        self._data = dict(self.DEFAULTS)
        self.load()

    def load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    self._data.update(json.load(f))
                # 一次性迁移：旧配置的固定语言改为跟随系统（仅在从未迁移过时执行）
                if not self._data.get("_lang_migrated", False):
                    self._data["language"] = "auto"
                    self._data["_lang_migrated"] = True
                    self.save()
        except Exception:
            pass

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self._data[name]
        except KeyError:
            return self.DEFAULTS.get(name)

    def set(self, name, value):
        self._data[name] = value
        self.save()


settings = AppSettings()

# -*- coding: utf-8 -*-
"""插件市场：以 GitHub/Gitee 仓库为后端（零服务器方案）。

- 索引文件 marketplace/plugins-index.json 托管在项目仓库
- 插件作者把插件文件放到任意可公开下载的地址（通常是自己仓库），
  再向项目仓库提交 PR 在索引中添加条目，合并后即上架
- 客户端从双源拉取索引（GitHub raw 优先，Gitee 兜底，国内可达），
  安装时下载插件文件并校验 sha256，复用本地插件导入管线
- 索引拉取结果缓存到本地，离线时显示上次的内容
"""
import hashlib
import json
import os
import tempfile
import threading

import requests
from PySide6.QtCore import QObject, Signal

from app.services.logger import log
from app.services.plugins import plugins_dir
from app.services.updater import _ver_tuple

INDEX_SOURCES = [
    "https://raw.githubusercontent.com/Carlown/NetPulse/master/marketplace/plugins-index.json",
    "https://gitee.com/carlown/netpulse/raw/master/marketplace/plugins-index.json",
]
# 索引在线编辑入口（发布插件用）
INDEX_EDIT_URL = "https://github.com/Carlown/NetPulse/edit/master/marketplace/plugins-index.json"

_TIMEOUT = 10


def _cache_file() -> str:
    base = os.path.dirname(plugins_dir())
    return os.path.join(base, "market_cache.json")


def _base_url(index_url: str) -> str:
    return index_url.rsplit("/", 1)[0] + "/"


class MarketClient(QObject):
    """市场客户端：后台线程做网络，信号回主线程。"""

    index_ready = Signal(list, bool)      # 条目列表, 是否来自本地缓存
    fetch_error = Signal(str)             # 拉取失败（且无缓存）
    download_ready = Signal(dict, str)    # entry, 临时文件路径（主线程调用 import_from）
    download_failed = Signal(str, str)    # 插件ID, 错误消息

    # ---------- 索引 ----------
    def fetch_index(self):
        threading.Thread(target=self._fetch_work, daemon=True).start()

    def _fetch_work(self):
        last_err = ""
        for url in INDEX_SOURCES:
            try:
                r = requests.get(url, timeout=_TIMEOUT)
                r.raise_for_status()
                data = r.json()
                entries = self._parse_index(data)
                if entries is None:
                    last_err = "bad index format"
                    continue
                try:
                    with open(_cache_file(), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                except Exception:
                    pass
                self.index_ready.emit(entries, False)
                return
            except Exception as e:
                last_err = str(e)
        # 全部源失败 → 尝试本地缓存
        cached = self._load_cache()
        if cached is not None:
            self.index_ready.emit(cached, True)
        else:
            self.fetch_error.emit(last_err)

    @staticmethod
    def _parse_index(data) -> "list | None":
        try:
            entries = data.get("plugins", [])
            if not isinstance(entries, list):
                return None
            out = []
            for e in entries:
                if not isinstance(e, dict) or not e.get("id") or not e.get("file"):
                    continue
                out.append(e)
            return out
        except Exception:
            return None

    def _load_cache(self):
        try:
            with open(_cache_file(), "r", encoding="utf-8") as f:
                return self._parse_index(json.load(f))
        except Exception:
            return None

    # ---------- 安装 ----------
    def install(self, entry: dict):
        threading.Thread(target=self._install_work, args=(entry,), daemon=True).start()

    def _install_work(self, entry: dict):
        pid = entry.get("id", "?")
        # 解析插件文件地址：相对路径基于索引所在目录；也可填完整 URL
        f = entry.get("file", "")
        if f.startswith("http://") or f.startswith("https://"):
            url = f
        else:
            url = _base_url(INDEX_SOURCES[0]) + f
        try:
            r = requests.get(url, timeout=_TIMEOUT)
            r.raise_for_status()
            content = r.content
        except Exception as e:
            # GitHub 失败换 Gitee 源再试（相对路径场景）
            if not f.startswith("http"):
                try:
                    r2 = requests.get(_base_url(INDEX_SOURCES[1]) + f, timeout=_TIMEOUT)
                    r2.raise_for_status()
                    content = r2.content
                except Exception:
                    self.download_failed.emit(pid, str(e))
                    return
            else:
                self.download_failed.emit(pid, str(e))
                return
        # sha256 完整性校验（索引提供时强制校验，不匹配拒绝安装）
        expect = (entry.get("sha256") or "").strip().lower()
        if expect:
            got = hashlib.sha256(content).hexdigest()
            if got != expect:
                self.download_failed.emit(
                    pid, "sha256 mismatch: "
                    f"{got[:12]}... != {expect[:12]}...")
                return
        # 写入临时文件交给主线程导入
        try:
            name = f"{pid}.py"
            tmp = os.path.join(tempfile.mkdtemp(prefix="netpulse_market_"), name)
            with open(tmp, "wb") as fh:
                fh.write(content)
        except Exception as e:
            self.download_failed.emit(pid, str(e))
            return
        log.info(f"market: downloaded {pid} ({len(content)} bytes)")
        self.download_ready.emit(entry, tmp)

    # ---------- 版本状态 ----------
    @staticmethod
    def installed_state(entry: dict) -> str:
        """对比本地已装插件版本：'absent' | 'same' | 'update'。"""
        from app.services.plugins import plugin_manager
        rec = plugin_manager.record(entry.get("id", ""))
        if rec is None or rec.plugin is None:
            return "absent"
        try:
            local_v = _ver_tuple(str(getattr(rec.plugin, "version", "0")))
            remote_v = _ver_tuple(str(entry.get("version", "0")))
            return "same" if local_v >= remote_v else "update"
        except Exception:
            return "same"

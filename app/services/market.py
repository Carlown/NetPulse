# -*- coding: utf-8 -*-
"""插件市场：以 GitHub 仓库为后端（零服务器方案）。

- 索引文件 marketplace/plugins-index.json 托管在项目仓库
- 插件作者把插件文件放到任意可公开下载的地址（通常是自己仓库），
  再向项目仓库提交 PR 在索引中添加条目，合并后即上架
- 客户端拉取索引，安装时下载插件文件并校验 sha256，复用本地插件导入管线
- 索引拉取结果缓存到本地，离线时显示上次的内容
"""
import hashlib
import json
import os
import re
import tempfile
import threading
import time

import requests
from PySide6.QtCore import QObject, Signal

from app.services.logger import log
from app.services.plugins import plugins_dir
from app.services.updater import _ver_tuple

INDEX_SOURCES = [
    # GitHub Contents API：内容实时（无 CDN 缓存延迟），匿名限额 60 次/小时，够日常刷新
    ("https://api.github.com/repos/Carlown/NetPulse/contents/marketplace/plugins-index.json?ref=master", "api"),
    # raw 直链兜底（可能有几分钟 CDN 延迟，但无限额）
    ("https://raw.githubusercontent.com/Carlown/NetPulse/master/marketplace/plugins-index.json", "raw"),
]
# 索引在线编辑入口（发布插件用）
INDEX_EDIT_URL = "https://github.com/Carlown/NetPulse/edit/master/marketplace/plugins-index.json"

# 浏览器一键授权（Device Flow）用的 OAuth App Client ID。
# 项目维护者在 GitHub → Settings → Developer settings → OAuth Apps 注册一次，
# 把 Client ID 填到这里即可；发布插件的用户将全程无需手动管理 Token。
GITHUB_OAUTH_CLIENT_ID = "Ov23licX0P0zdKXS36yC"

_GH_LOGIN = "https://github.com/login"


def device_flow_start() -> dict:
    """启动 GitHub 设备授权：返回 device_code/user_code/verification_uri 等。"""
    if not GITHUB_OAUTH_CLIENT_ID:
        raise ValueError("OAuth client id not configured")
    r = requests.post(f"{_GH_LOGIN}/device/code",
                      headers={"Accept": "application/json"},
                      data={"client_id": GITHUB_OAUTH_CLIENT_ID,
              "scope": "public_repo workflow"},
                      timeout=15)
    r.raise_for_status()
    return r.json()


def device_flow_poll(device_code: str, interval: int, expires_in: int) -> str:
    """轮询授权结果直到用户在浏览器确认，返回 access_token；拒绝/超时抛异常。"""
    import time as _t
    deadline = _t.time() + int(expires_in or 900)
    iv = max(int(interval or 5), 1)
    while _t.time() < deadline:
        r = requests.post(f"{_GH_LOGIN}/oauth/access_token",
                          headers={"Accept": "application/json"},
                          data={"client_id": GITHUB_OAUTH_CLIENT_ID,
                                "device_code": device_code,
                                "grant_type": "urn:ietf:params:oauth:grant-type:device_code"},
                          timeout=15)
        d = r.json()
        err = d.get("error")
        if err == "authorization_pending":
            _t.sleep(iv)
            continue
        if err == "slow_down":
            iv += 5
            _t.sleep(iv)
            continue
        if err:
            raise ValueError(err)
        return d["access_token"]
    raise ValueError("authorization timeout")

_TIMEOUT = 10
_MAX_PLUGIN_BYTES = 2 * 1024 * 1024
_MARKET_PLUGIN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def is_valid_market_plugin_id(value) -> bool:
    """市场插件 ID 只能是安全的 ASCII 文件名片段。"""
    return type(value) is str and bool(_MARKET_PLUGIN_ID_RE.fullmatch(value))


def _fetch_index_raw(url: str, kind: str):
    """拉取并解析索引，返回 dict；失败抛异常。kind: api | raw。"""
    headers = {"User-Agent": "NetPulse", "Cache-Control": "no-cache"}
    # Authenticated requests avoid GitHub's low anonymous API rate limit when
    # the user has already authorized publishing from this installation.
    try:
        from app.services.settings import settings
        token = str(settings.github_token or "").strip()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    except Exception:
        pass
    if kind == "api":
        r = requests.get(url, timeout=_TIMEOUT,
                         headers={**headers, "Accept": "application/vnd.github+json"})
        r.raise_for_status()
        import base64
        payload = r.json()
        text = base64.b64decode(payload["content"]).decode("utf-8")
    else:
        # A five-minute bucket can serve an old raw.githubusercontent.com
        # response immediately after a publish. Use a unique query each time.
        bust = f"{url}{'&' if '?' in url else '?'}cachebust={time.time_ns()}"
        r = requests.get(bust, timeout=_TIMEOUT, headers=headers)
        r.raise_for_status()
        text = r.text
    data = json.loads(text)
    if not isinstance(data, dict) or "plugins" not in data:
        raise ValueError("bad index format")
    return data


def _cache_file() -> str:
    base = os.path.dirname(plugins_dir())
    return os.path.join(base, "market_cache.json")


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
        for url, kind in INDEX_SOURCES:
            try:
                data = _fetch_index_raw(url, kind)
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
                if not isinstance(e, dict):
                    continue
                pid = e.get("id")
                file_value = e.get("file")
                digest = str(e.get("sha256") or "")
                if (not is_valid_market_plugin_id(pid)
                        or type(file_value) is not str or not file_value.strip()
                        or re.fullmatch(r"[0-9a-fA-F]{64}", digest) is None):
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
        if not is_valid_market_plugin_id(pid):
            self.download_failed.emit(str(pid), "invalid plugin id")
            return
        expect = str(entry.get("sha256") or "").strip().lower()
        if re.fullmatch(r"[0-9a-f]{64}", expect) is None:
            self.download_failed.emit(pid, "missing or invalid sha256")
            return
        # 解析插件文件地址：相对路径基于仓库 marketplace 目录（raw 直链）；也可填完整 URL
        f = entry.get("file", "")
        if f.startswith("http://") or f.startswith("https://"):
            url = f
        else:
            url = ("https://raw.githubusercontent.com/Carlown/NetPulse"
                   f"/master/marketplace/{f}")
        try:
            with requests.get(url, timeout=_TIMEOUT, stream=True) as r:
                r.raise_for_status()
                size_header = int(r.headers.get("Content-Length", 0) or 0)
                if size_header > _MAX_PLUGIN_BYTES:
                    raise ValueError("plugin file exceeds 2 MiB limit")
                content_buf = bytearray()
                for chunk in r.iter_content(64 * 1024):
                    if not chunk:
                        continue
                    content_buf.extend(chunk)
                    if len(content_buf) > _MAX_PLUGIN_BYTES:
                        raise ValueError("plugin file exceeds 2 MiB limit")
                content = bytes(content_buf)
        except Exception as e:
            self.download_failed.emit(pid, str(e))
            return
        # sha256 完整性校验强制执行，不匹配拒绝安装。
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
        """对比本地已装插件版本：'absent' | 'same' | 'update' | 'disabled'。"""
        from app.services.plugins import plugin_manager
        rec = plugin_manager.record(entry.get("id", ""))
        if rec is None:
            return "absent"
        # 已安装但被禁用：显示"启用"而非"安装"
        if rec.disabled:
            return "disabled"
        # 已安装但未加载（非禁用）：用缓存的版本号比较
        if rec.plugin is None:
            try:
                local_v = _ver_tuple(str(rec.display_version or "0"))
                remote_v = _ver_tuple(str(entry.get("version", "0")))
                return "same" if local_v >= remote_v else "update"
            except Exception:
                return "same"
        try:
            local_v = _ver_tuple(str(getattr(rec.plugin, "version", "0")))
            remote_v = _ver_tuple(str(entry.get("version", "0")))
            return "same" if local_v >= remote_v else "update"
        except Exception:
            return "same"

"""检查更新：查询 GitHub Releases 最新版本，发现新版时弹窗提示。"""
import threading

import requests
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices

APP_VERSION = "1.0.5"
REPO = "Carlown/NetPulse"
RELEASES_URL = f"https://github.com/{REPO}/releases"
LATEST_URL = f"https://github.com/{REPO}/releases/latest"
_API_URL = f"https://api.github.com/repos/{REPO}/releases/latest"

_keep_alive = []  # 防止后台检查器被 GC


def _ver_tuple(v: str):
    nums = []
    for part in v.strip().lstrip("vV").split("."):
        digits = ""
        for ch in part:
            if ch.isdigit():
                digits += ch
            else:
                break
        nums.append(int(digits) if digits else 0)
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def is_newer(latest: str, current: str = APP_VERSION) -> bool:
    try:
        return _ver_tuple(latest) > _ver_tuple(current)
    except Exception:
        return False


class _Checker(QObject):
    done = Signal(dict)

    def go(self):
        threading.Thread(target=self._work, daemon=True).start()

    def _work(self):
        try:
            r = requests.get(_API_URL, timeout=8,
                             headers={"Accept": "application/vnd.github+json"})
            r.raise_for_status()
            d = r.json()
            tag = str(d.get("tag_name", ""))
            self.done.emit({"ok": True, "tag": tag,
                            "url": d.get("html_url") or LATEST_URL,
                            "newer": is_newer(tag)})
        except Exception as e:
            self.done.emit({"ok": False, "error": str(e)})


def check_for_updates(parent=None, manual: bool = False):
    """后台检查 GitHub 最新 Release。

    manual=False（启动自动检查）：仅在有新版本时弹窗；
    manual=True（设置页手动检查）：无论结果都给出提示。
    """
    from app.ui.i18n import L

    c = _Checker()
    _keep_alive.append(c)

    def on_done(d):
        try:
            _keep_alive.remove(c)
        except ValueError:
            pass
        if not d.get("ok"):
            if manual:
                from qfluentwidgets import InfoBar
                InfoBar.error(L("检查更新失败", "Update check failed"),
                              L(f"无法连接 GitHub：{d.get('error', '')}",
                                f"Cannot reach GitHub: {d.get('error', '')}"),
                              parent=parent, duration=5000)
            return
        if d.get("newer"):
            _show_update_dialog(parent, d["tag"], d["url"], L)
        elif manual:
            from qfluentwidgets import InfoBar
            InfoBar.success(L("已是最新版本", "Up to date"),
                            L(f"当前版本 v{APP_VERSION}，与 GitHub 最新版本一致。",
                              f"You are on the latest version (v{APP_VERSION})."),
                            parent=parent, duration=4000)

    c.done.connect(on_done)
    c.go()


def _show_update_dialog(parent, tag, url, L):
    from qfluentwidgets import MessageBox

    box = MessageBox(L(f"发现新版本 {tag}", f"New version {tag} available"),
                     L(f"当前版本 v{APP_VERSION}，GitHub 已发布 {tag}。\n是否前往下载更新？",
                       f"Current version v{APP_VERSION}; {tag} is now on GitHub.\n"
                       f"Open the download page?"),
                     parent)
    box.yesButton.setText(L("去更新", "Update"))
    box.cancelButton.setText(L("稍后再说", "Later"))
    if box.exec():
        QDesktopServices.openUrl(QUrl(url or LATEST_URL))

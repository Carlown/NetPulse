"""双语文案助手：支持跟随系统语言。"""
from PySide6.QtCore import QLocale

from app.services.settings import settings


def current_lang() -> str:
    """解析当前语言：auto 时按系统区域设置检测（中文系统→zh-CN，其余→en-US）。"""
    lang = settings.language
    if lang == "auto":
        name = QLocale.system().name()  # 如 "zh_CN" / "en_US"
        return "zh-CN" if name.startswith("zh") else "en-US"
    return lang


def L(zh: str, en: str) -> str:
    return zh if current_lang() == "zh-CN" else en

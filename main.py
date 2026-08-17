"""NetPulse — 合法授权网络压力测试与性能监控工具（Python/Fluent 版）。"""
import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from qfluentwidgets import Theme, setTheme, setThemeColor

from app.services.logger import log
from app.services.monitor import monitor
from app.services.settings import settings
from app.ui.disclaimer import DisclaimerDialog
from app.ui.i18n import L
from app.ui.main_window import MainWindow


def apply_qfluent_language():
    try:
        from qfluentwidgets import Language, setLanguage
        from app.ui.i18n import current_lang
        if current_lang() == "en-US":
            setLanguage(Language.EN)
        else:
            setLanguage(getattr(Language, "ZH_CN", Language.ZH_CN))
    except Exception:
        pass


def resource_path(rel: str) -> str:
    """兼容源码运行与 PyInstaller 打包（--onefile 时资源解压到 _MEIPASS）。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def main():
    app = QApplication(sys.argv)
    # 应用图标：窗口左上角 + 任务栏
    ico = resource_path("app.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))
    setThemeColor("#0078D4")
    setTheme(Theme.DARK if settings.theme == "dark" else Theme.LIGHT)
    apply_qfluent_language()

    win = MainWindow()
    win.show()  # 必须先显示主窗口，免责声明对话框才能依附可见父窗口正常居中显示

    # 命令行指定起始页：--page monitor / stress / collab
    if "--page" in sys.argv:
        page = sys.argv[sys.argv.index("--page") + 1].lower() if len(sys.argv) > sys.argv.index("--page") + 1 else ""
        target = {"monitor": win.monitor, "stress": win.stress,
                  "collab": win.collab, "home": win.dashboard}.get(page)
        if target is not None:
            win.switchTo(target)

    if not settings.disclaimer_accepted:
        dlg = DisclaimerDialog(win)
        if not dlg.exec():
            log.info("用户未同意免责声明，程序退出。")
            return 0
        settings.set("disclaimer_accepted", True)
        log.info("用户已同意免责声明。")

    monitor.start()
    log.info("NetPulse 启动。")

    # 启动 3 秒后静默检查更新（仅在有新版本时弹窗）
    def _auto_update_check():
        try:
            from app.services.updater import check_for_updates
            check_for_updates(parent=win, manual=False)
        except Exception:
            pass

    from PySide6.QtCore import QTimer
    QTimer.singleShot(3000, _auto_update_check)

    code = app.exec()
    monitor.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())

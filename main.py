"""NetPulse — 合法授权网络压力测试与性能监控工具（Python/Fluent 版）。"""
import os
import sys

# 仅导入最核心、最轻量的模块，确保启动画面能第一时间显示
from PySide6.QtCore import QTimer, QSize
from PySide6.QtWidgets import QApplication
from app.ui.splash import create_splash

SINGLE_INSTANCE_KEY = "NetPulse_SingleInstance_Key"


def resource_path(rel: str) -> str:
    """兼容源码运行与 PyInstaller 打包。"""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def is_already_running() -> bool:
    """检测是否已有实例在运行；如果有，发送消息让它显示窗口后返回 True。"""
    from PySide6.QtNetwork import QLocalSocket
    socket = QLocalSocket()
    socket.connectToServer(SINGLE_INSTANCE_KEY)
    if socket.waitForConnected(80):  # 本地连接极快，80ms 足够
        socket.write(b"show")
        socket.flush()
        socket.waitForBytesWritten(200)
        socket.disconnectFromServer()
        return True
    return False


def main():
    # ① 第一时间创建 QApplication 并显示启动画面
    app = QApplication(sys.argv)
    splash = create_splash()  # 这是双击后用户看到的第一样东西

    # ② 再做单实例检测（splash 已经在屏幕上了）
    if is_already_running():
        splash.close()
        return 0

    # 便捷函数：设置进度 + 双语状态文字
    def step(percent, zh, en):
        from app.ui.i18n import L
        splash.set_progress(percent, L(zh, en))

    step(10, "正在启动...", "Starting...")

    # ③ 应用图标
    from PySide6.QtGui import QIcon
    step(25, "加载资源...", "Loading resources...")
    ico = resource_path("app.ico")
    if os.path.exists(ico):
        app.setWindowIcon(QIcon(ico))

    # ④ 主题
    from qfluentwidgets import Theme, setTheme, setThemeColor
    from app.services.settings import settings
    from app.ui.i18n import L, current_lang
    step(45, "加载主题...", "Loading theme...")
    setThemeColor("#0078D4")
    setTheme(Theme.DARK if settings.theme == "dark" else Theme.LIGHT)
    try:
        from qfluentwidgets import Language, setLanguage
        if current_lang() == "en-US":
            setLanguage(Language.EN)
        else:
            setLanguage(getattr(Language, "ZH_CN", Language.ZH_CN))
    except Exception:
        pass

    # ⑤ 创建主窗口
    from app.ui.main_window import MainWindow
    step(65, "初始化界面...", "Initializing interface...")
    win = MainWindow()

    # ⑥ 单实例服务器
    from PySide6.QtNetwork import QLocalServer

    class SingleInstanceServer(QLocalServer):
        def __init__(self, main_window):
            super().__init__()
            self.main_window = main_window
            self.newConnection.connect(self._on_new_connection)

        def _on_new_connection(self):
            socket = self.nextPendingConnection()
            if socket:
                socket.waitForReadyRead(500)
                self.main_window._show_from_tray()
                socket.disconnectFromServer()

    step(80, "配置服务...", "Configuring services...")
    QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
    local_server = SingleInstanceServer(win)
    if not local_server.listen(SINGLE_INSTANCE_KEY):
        from app.services.logger import log
        log.warning(f"单实例服务器启动失败: {local_server.errorString()}")
    app._single_instance_server = local_server

    # ⑦ 命令行指定起始页
    step(90, "即将就绪...", "Almost ready...")
    if "--page" in sys.argv:
        page = sys.argv[sys.argv.index("--page") + 1].lower() if len(sys.argv) > sys.argv.index("--page") + 1 else ""
        target = {"monitor": win.monitor, "stress": win.stress,
                  "collab": win.collab, "home": win.dashboard}.get(page)
        if target is not None:
            win.switchTo(target)

    # ⑧ 完成启动流程
    step(100, "准备就绪", "Ready")

    # 记录主窗口引用
    splash.finish_with_window(win)

    def complete_startup():
        """完成启动：关闭 splash，显示主窗口。"""
        splash.finish_splash()
        # 立即显示主窗口
        win.resize(QSize(1240, 800))
        win.show()
        win.raise_()
        win.activateWindow()
        # 多次延迟确保尺寸生效（应对 FluentWindow 初始化布局可能的 resize）
        QTimer.singleShot(50, lambda: win.resize(QSize(1240, 800)))
        QTimer.singleShot(200, post_startup)

    def post_startup():
        """主窗口显示后的处理。"""
        # 再次确保尺寸正确
        win.resize(QSize(1240, 800))
        
        # 免责声明（首次启动）
        if not settings.disclaimer_accepted:
            from app.ui.disclaimer import DisclaimerDialog
            dlg = DisclaimerDialog(win)
            if not dlg.exec():
                from app.services.logger import log
                log.info("用户未同意免责声明，程序退出。")
                app.quit()
                return
            settings.set("disclaimer_accepted", True)
            from app.services.logger import log
            log.info("用户已同意免责声明。")

    # 让进度条在 100% 停留一会儿再关闭 splash
    QTimer.singleShot(350, complete_startup)

    # ⑨ 启动后台服务
    from app.services.monitor import monitor
    from app.services.logger import log
    monitor.start()
    log.info("NetPulse 启动。")

    # 启动 3 秒后静默检查更新
    def _auto_update_check():
        try:
            from app.services.updater import check_for_updates
            check_for_updates(parent=win, manual=False)
        except Exception:
            pass

    QTimer.singleShot(3000, _auto_update_check)

    code = app.exec()
    monitor.stop()
    return code


if __name__ == "__main__":
    sys.exit(main())

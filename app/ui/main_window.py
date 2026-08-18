"""主窗口：FluentWindow 侧边导航 + Mica 效果。"""
import os
import sys

from PySide6.QtCore import QSize
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QMenu, QSystemTrayIcon
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

from app.services.settings import settings
from app.ui.collab_view import CollabView
from app.ui.dashboard import DashboardView
from app.ui.i18n import L
from app.ui.monitor_view import MonitorView
from app.ui.settings_view import SettingsView
from app.ui.stress_view import StressView

MON_ICON = getattr(FIF, "DIAGNOSTICS", getattr(FIF, "HEART", FIF.DEVELOPER_TOOLS))


def _get_icon_path():
    """获取应用图标路径。"""
    if getattr(sys, "_MEIPASS", None):
        return os.path.join(sys._MEIPASS, "app.ico")
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "app.ico")


class MainWindow(FluentWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("NetPulse")
        self.resize(QSize(1240, 800))
        self.setMinimumSize(QSize(1000, 680))

        self.dashboard = DashboardView(self)
        self.stress = StressView(self)
        self.collab = CollabView(self)
        self.monitor = MonitorView(self)
        self.settingsView = SettingsView(self)

        self.init_navigation()
        self.init_window()
        self._init_tray()

    def init_navigation(self):
        self.addSubInterface(self.dashboard, FIF.HOME, L("主页", "Home"))
        self.addSubInterface(self.stress, FIF.SPEED_HIGH, L("压力测试", "Stress Test"))
        self.addSubInterface(self.collab, FIF.CONNECT, L("协同测试", "Collaborative"))
        self.addSubInterface(self.monitor, MON_ICON, L("监控面板", "Monitor"))
        self.addSubInterface(self.settingsView, FIF.SETTING, L("设置", "Settings"),
                             NavigationItemPosition.BOTTOM)

    def init_window(self):
        try:
            self.setMicaEffectEnabled(True)
        except Exception:
            pass

    def _init_tray(self):
        """初始化系统托盘。"""
        icon_path = _get_icon_path()
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("NetPulse")

        tray_menu = QMenu()

        show_action = QAction(L("显示主窗口", "Show Window"), self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        quit_action = QAction(L("退出", "Quit"), self)
        quit_action.triggered.connect(self._quit_app)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        """托盘图标双击显示窗口。"""
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_from_tray()

    def _show_from_tray(self):
        """从托盘/最小化状态恢复显示窗口。"""
        from PySide6.QtCore import Qt
        # 如果窗口被隐藏（关闭时最小化到托盘的情况），先显示出来
        if not self.isVisible():
            self.show()
        # 如果窗口最小化了，恢复正常大小
        if self.isMinimized():
            self.showNormal()
        # 激活窗口并置于最前
        self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
        self.activateWindow()
        self.raise_()
        self.show()

    def _quit_app(self):
        """从托盘退出应用。"""
        self.tray_icon.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def closeEvent(self, event):
        """重写关闭事件，根据配置决定最小化到托盘还是退出。"""
        if settings.minimize_to_tray and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                "NetPulse",
                L("程序已最小化到托盘，右键托盘图标可退出",
                  "Minimized to tray, right-click tray icon to quit"),
                QSystemTrayIcon.Information,
                2000
            )
        else:
            event.accept()

    def go_stress(self):
        self.switchTo(self.stress)

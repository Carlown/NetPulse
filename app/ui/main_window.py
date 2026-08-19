"""主窗口：FluentWindow 侧边导航 + Mica 效果。"""
import os
import sys

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QSystemTrayIcon
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition, RoundMenu, Action, isDarkTheme

from app.services.settings import settings
from app.ui.busy_overlay import BusyOverlay
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
        self._default_size = QSize(1240, 800)
        self._minimum_size = QSize(1000, 680)
        self.resize(self._default_size)
        self.setMinimumSize(self._minimum_size)
        self._first_show = True
        self._tray_notified = False  # 标记托盘提示是否已弹过（每个运行会话只弹一次）

        self.dashboard = DashboardView(self)
        self.stress = StressView(self)
        self.collab = CollabView(self)
        self.monitor = MonitorView(self)
        self.settingsView = SettingsView(self)

        self.init_navigation()
        self.init_window()
        self._init_tray()

        # BusyOverlay 创建为子控件，但初始隐藏
        # 使用 QTimer.singleShot 确保在窗口完全构建后再创建
        self._busy_overlay = None

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

    def _ensure_overlay(self):
        """确保 overlay 已创建（首次调用时在窗口显示后创建）。"""
        if self._busy_overlay is None:
            self._busy_overlay = BusyOverlay(self)
            self._busy_overlay.setGeometry(0, 0, self.width(), self.height())
            self._busy_overlay.hide()
        return self._busy_overlay

    def _init_tray(self):
        """初始化系统托盘。"""
        icon_path = _get_icon_path()
        self.tray_icon = QSystemTrayIcon(self)
        if os.path.exists(icon_path):
            self.tray_icon.setIcon(QIcon(icon_path))
        else:
            self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("NetPulse")

        # 使用 RoundMenu 自动适配深色/浅色主题
        tray_menu = RoundMenu(parent=self)

        show_action = Action(FIF.VIEW, L("显示主窗口", "Show Window"), self)
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addAction(show_action)

        tray_menu.addSeparator()

        quit_action = Action(FIF.CLOSE, L("退出", "Quit"), self)
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
        if not self.isVisible():
            self.show()
        if self.isMinimized():
            self.showNormal()
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
            # 每个运行会话只弹一次提示，避免每次关闭都打扰用户
            if not self._tray_notified:
                self._tray_notified = True
                self.tray_icon.showMessage(
                    "NetPulse",
                    L("程序已最小化到托盘，右键托盘图标可退出",
                      "Minimized to tray, right-click tray icon to quit"),
                    QSystemTrayIcon.Information,
                    2500
                )
        else:
            event.accept()

    def go_stress(self):
        self.switchTo(self.stress)

    def resizeEvent(self, event):
        """窗口大小变化时同步更新 overlay 大小。"""
        super().resizeEvent(event)
        overlay = getattr(self, "_busy_overlay", None)
        if overlay and overlay.isVisible():
            overlay.setGeometry(0, 0, self.width(), self.height())

    def showEvent(self, event):
        """窗口首次显示时创建 overlay 并确保尺寸正确。"""
        super().showEvent(event)
        if self._first_show:
            self._first_show = False
            # 多次延迟强制确保窗口尺寸正确（应对 FluentWindow 初始化布局可能的 resize）
            for delay in [0, 30, 100, 250, 500]:
                QTimer.singleShot(delay, self._ensure_correct_size)
        self._ensure_overlay()
    
    def _ensure_correct_size(self):
        """确保窗口尺寸正确（仅在窗口比默认尺寸小时调整，不覆盖用户手动调整）。"""
        if self.isVisible() and not self.isMaximized() and not self.isMinimized():
            current = self.size()
            target = self._default_size
            # 如果当前尺寸比默认小，才调整（避免覆盖用户手动放大）
            if current.width() < target.width() or current.height() < target.height():
                self.resize(target)

    def show_busy(self, text: str = "", sub_text: str = ""):
        """显示全局加载遮罩。"""
        overlay = self._ensure_overlay()
        overlay.show(text, sub_text)

    def hide_busy(self):
        """隐藏全局加载遮罩。"""
        overlay = getattr(self, "_busy_overlay", None)
        if overlay:
            overlay.hide()

    def set_busy_text(self, text: str, sub_text: str = ""):
        """更新加载遮罩的文字。"""
        overlay = getattr(self, "_busy_overlay", None)
        if overlay:
            overlay.set_text(text, sub_text)

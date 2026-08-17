"""主窗口：FluentWindow 侧边导航 + Mica 效果。"""
from PySide6.QtCore import QSize
from qfluentwidgets import FluentIcon as FIF
from qfluentwidgets import FluentWindow, NavigationItemPosition

from app.ui.collab_view import CollabView
from app.ui.dashboard import DashboardView
from app.ui.i18n import L
from app.ui.monitor_view import MonitorView
from app.ui.settings_view import SettingsView
from app.ui.stress_view import StressView

MON_ICON = getattr(FIF, "DIAGNOSTICS", getattr(FIF, "HEART", FIF.DEVELOPER_TOOLS))


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

    def go_stress(self):
        self.switchTo(self.stress)

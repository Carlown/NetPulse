"""设置页：主题/语言/默认参数/日志管理/检查更新/作者。"""
from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QCursor, QFont
from PySide6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, InfoBar,
                            PushButton, ScrollArea, SimpleCardWidget, SpinBox,
                            StrongBodyLabel, SubtitleLabel, SwitchButton,
                            setTheme, setThemeColor, Theme, IconWidget,
                            FluentIcon, isDarkTheme)

from app.services.logger import log
from app.services.settings import settings
from app.services.updater import APP_VERSION, LATEST_URL, check_for_updates
from app.ui.disclaimer import DisclaimerDialog
from app.ui.i18n import L

AUTHOR_NAME = "Carlown"
AUTHOR_URL = "https://github.com/Carlown"


class SettingRow(QWidget):
    def __init__(self, title, desc, control, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 4, 0, 4)
        col = QVBoxLayout()
        t = BodyLabel(title, self)
        d = CaptionLabel(desc, self)
        d.setWordWrap(True)
        col.addWidget(t)
        col.addWidget(d)
        lay.addLayout(col, 1)
        lay.addWidget(control)


class ClickableCard(SimpleCardWidget):
    """可点击的卡片，整个区域可点击，带悬停效果和右侧图标。"""

    clicked = Signal()

    def __init__(self, parent=None):
        self._hover = False  # 必须在 super().__init__ 之前初始化，因为父类会调用 _normalBackgroundColor()
        super().__init__(parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))

    def enterEvent(self, event):
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    def _normalBackgroundColor(self):
        from qfluentwidgets import isDarkTheme
        if isDarkTheme():
            return QColor(255, 255, 255, 13) if not self._hover else QColor(255, 255, 255, 20)
        else:
            return QColor(255, 255, 255) if not self._hover else QColor(245, 245, 250)


from PySide6.QtGui import QColor


class SettingsView(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settingsView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)
        root.addWidget(SubtitleLabel(L("设置", "Settings"), self.view))

        # 外观
        appear = SimpleCardWidget(self.view)
        al = QVBoxLayout(appear)
        al.setContentsMargins(20, 16, 20, 16)
        al.setSpacing(4)
        al.addWidget(StrongBodyLabel(L("外观", "Appearance"), appear))
        self.darkSwitch = SwitchButton()
        self.darkSwitch.setChecked(settings.theme == "dark")
        self.darkSwitch.checkedChanged.connect(self._theme_changed)
        al.addWidget(SettingRow(L("深色模式", "Dark mode"),
                                L("Fluent 深色主题", "Fluent dark theme"), self.darkSwitch, appear))
        self.traySwitch = SwitchButton()
        self.traySwitch.setChecked(settings.minimize_to_tray)
        self.traySwitch.checkedChanged.connect(
            lambda v: settings.set("minimize_to_tray", v))
        al.addWidget(SettingRow(L("关闭时最小化到托盘", "Minimize to tray on close"),
                                L("关闭窗口时程序将驻留系统托盘", "Keep app running in system tray when closing window"), self.traySwitch, appear))
        self.autoUpdateSwitch = SwitchButton()
        self.autoUpdateSwitch.setChecked(settings.auto_check_updates)
        self.autoUpdateSwitch.checkedChanged.connect(
            lambda v: settings.set("auto_check_updates", v))
        al.addWidget(SettingRow(L("启动时自动检查更新", "Auto-check for updates on launch"),
                                L("发现新版本时弹窗提示", "Show notification when new version is available"), self.autoUpdateSwitch, appear))
        self.langCombo = ComboBox()
        self.langCombo.addItems([L("跟随系统", "Auto (system)"), "简体中文", "English"])
        self.langCombo.setCurrentIndex(
            {"auto": 0, "zh-CN": 1, "en-US": 2}.get(settings.language, 0))
        self.langCombo.currentIndexChanged.connect(self._lang_changed)
        al.addWidget(SettingRow(L("界面语言", "Language"),
                                L("跟随系统语言自动选择（默认）", "Auto-follow system language (default)"), self.langCombo, appear))
        root.addWidget(appear)

        # 默认参数
        defaults = SimpleCardWidget(self.view)
        dl = QVBoxLayout(defaults)
        dl.setContentsMargins(20, 16, 20, 16)
        dl.setSpacing(4)
        dl.addWidget(StrongBodyLabel(L("默认参数", "Defaults"), defaults))
        self.threadSpin = SpinBox()
        self.threadSpin.setRange(1, 1024)
        self.threadSpin.setValue(settings.default_threads)
        self.threadSpin.valueChanged.connect(lambda v: settings.set("default_threads", v))
        dl.addWidget(SettingRow(L("默认并发线程", "Default concurrency"),
                                L("新会话的初始线程数", "Initial thread count"), self.threadSpin, defaults))
        self.timeoutSpin = SpinBox()
        self.timeoutSpin.setRange(500, 60000)
        self.timeoutSpin.setValue(settings.default_timeout_ms)
        self.timeoutSpin.setSingleStep(500)
        self.timeoutSpin.valueChanged.connect(lambda v: settings.set("default_timeout_ms", v))
        dl.addWidget(SettingRow(L("超时(ms)", "Timeout (ms)"),
                                L("单请求超时时间", "Per-request timeout"), self.timeoutSpin, defaults))
        self.rateSpin = SpinBox()
        self.rateSpin.setRange(1, 100000)
        self.rateSpin.setValue(settings.default_rate)
        self.rateSpin.valueChanged.connect(lambda v: settings.set("default_rate", v))
        dl.addWidget(SettingRow(L("默认速率上限(QPS)", "Default rate cap"),
                                L("令牌桶填充速率", "Token bucket fill rate"), self.rateSpin, defaults))
        root.addWidget(defaults)

        # 日志
        logcard = SimpleCardWidget(self.view)
        ll = QVBoxLayout(logcard)
        ll.setContentsMargins(20, 16, 20, 16)
        ll.setSpacing(4)
        ll.addWidget(StrongBodyLabel(L("审计日志", "Audit Log"), logcard))
        self.logPathLabel = CaptionLabel(log.file_path, logcard)
        self.logPathLabel.setWordWrap(True)
        ll.addWidget(self.logPathLabel)
        brow = QHBoxLayout()
        self.exportBtn = PushButton(L("导出日志", "Export Log"), logcard)
        self.exportBtn.clicked.connect(self._export)
        self.openBtn = PushButton(L("打开日志目录", "Open Log Folder"), logcard)
        self.openBtn.clicked.connect(self._open_dir)
        brow.addWidget(self.exportBtn)
        brow.addWidget(self.openBtn)
        brow.addStretch(1)
        ll.addLayout(brow)
        root.addWidget(logcard)

        # 关于
        about = SimpleCardWidget(self.view)
        bl = QVBoxLayout(about)
        bl.setContentsMargins(20, 16, 20, 16)
        bl.addWidget(StrongBodyLabel(L("关于", "About"), about))
        bl.addWidget(BodyLabel(f"NetPulse v{APP_VERSION}", about))
        bl.addWidget(CaptionLabel(L("仅用于合法授权的性能测试。", "For legally authorized testing only."), about))
        brow = QHBoxLayout()
        self.disclaimerBtn = PushButton(L("查看免责声明", "View Disclaimer"), about)
        self.disclaimerBtn.clicked.connect(lambda: DisclaimerDialog(self.window()).exec())
        self.updateBtn = PushButton(L("检查更新", "Check for Updates"), about)
        self.updateBtn.clicked.connect(self._check_update)
        brow.addWidget(self.disclaimerBtn)
        brow.addWidget(self.updateBtn)
        brow.addStretch(1)
        bl.addLayout(brow)
        root.addWidget(about)

        # 作者（可点击卡片，整个区域跳转）
        author = ClickableCard(self.view)
        author.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(AUTHOR_URL)))
        aul = QHBoxLayout(author)
        aul.setContentsMargins(20, 16, 20, 16)
        aul.setSpacing(12)
        # 左侧：作者信息
        info_col = QVBoxLayout()
        info_col.setSpacing(2)
        info_col.addWidget(StrongBodyLabel(L("作者", "Author"), author))
        author_name = BodyLabel(AUTHOR_NAME, author)
        author_name_font = QFont()
        author_name_font.setPointSize(12)
        author_name.setFont(author_name_font)
        info_col.addWidget(author_name)
        gh_label = CaptionLabel(L(f"GitHub 主页：{AUTHOR_URL}", f"GitHub: {AUTHOR_URL}"), author)
        gh_label.setWordWrap(True)
        info_col.addWidget(gh_label)
        aul.addLayout(info_col, 1)
        # 右侧：链接图标（自动适配主题色）
        self.linkIcon = IconWidget(FluentIcon.LINK, author)
        self.linkIcon.setFixedSize(24, 24)
        aul.addWidget(self.linkIcon, 0, Qt.AlignVCenter)
        root.addWidget(author)

        root.addStretch(1)

    def _check_update(self):
        self.updateBtn.setEnabled(False)
        self.updateBtn.setText(L("检查中…", "Checking…"))
        from app.services.updater import check_for_updates as run_check

        def _done():
            self.updateBtn.setEnabled(True)
            self.updateBtn.setText(L("检查更新", "Check for Updates"))

        # check_for_updates 内部完成回调后界面即有提示，这里只恢复按钮状态
        run_check(parent=self.window(), manual=True)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(4000, _done)

    def _theme_changed(self, checked):
        setTheme(Theme.DARK if checked else Theme.LIGHT)
        settings.set("theme", "dark" if checked else "light")

    def _lang_changed(self, idx):
        settings.set("language", {0: "auto", 1: "zh-CN", 2: "en-US"}.get(idx, "auto"))
        try:
            from qfluentwidgets import setLanguage, Language
            from app.ui.i18n import current_lang
            setLanguage(Language.EN if current_lang() == "en-US"
                        else getattr(Language, "ZH_CN", Language.ZH_CN))
        except Exception:
            pass
        InfoBar.success(L("已保存", "Saved"),
                        L("界面语言将在重启后完全生效", "Language fully applies after restart"),
                        parent=self.window())

    def _export(self):
        path, _ = QFileDialog.getSaveFileName(self, L("导出日志", "Export log"),
                                              "netpulse-audit.log", "Log (*.log *.txt)")
        if path:
            n = log.export_text(path)
            InfoBar.success(L("导出成功", "Exported"), L(f"{n} 条记录", f"{n} entries"), parent=self.window())

    def _open_dir(self):
        import os
        os.startfile(os.path.dirname(log.file_path))

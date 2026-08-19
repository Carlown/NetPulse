"""通用加载等待遮罩：半透明遮罩 + 居中卡片（Win11 风格转圈 + 提示文字）。

作为子控件覆盖在父窗口上，不会弹出独立窗口。自动适配深色/浅色主题。

用法：
    overlay = BusyOverlay(parent_widget)
    overlay.show("请稍候...", "Please wait...")
    # ... 执行耗时操作（建议放到后台线程）
    overlay.hide()
"""
from PySide6.QtCore import Qt, QEvent
from PySide6.QtGui import QColor, QPainter, QFont
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout,
                               QGraphicsDropShadowEffect, QApplication)
from qfluentwidgets import IndeterminateProgressRing, isDarkTheme, qconfig

from app.ui.i18n import L


class BusyOverlay(QWidget):
    """半透明遮罩覆盖层 - 作为子控件嵌入父窗口，不创建独立窗口。自动适配主题。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, False)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setVisible(False)
        self._event_filter_installed = False

        # 居中卡片容器
        self._card = QWidget(self)
        self._card.setObjectName("busyCard")

        # 阴影效果（颜色在 _apply_theme 中设置）
        self._shadow = QGraphicsDropShadowEffect(self._card)
        self._shadow.setBlurRadius(50)
        self._shadow.setOffset(0, 10)
        self._card.setGraphicsEffect(self._shadow)

        # 卡片内部布局
        card_layout = QHBoxLayout(self._card)
        card_layout.setContentsMargins(28, 24, 36, 24)
        card_layout.setSpacing(20)

        # Win11 风格的不确定进度环（颜色由主题自动管理）
        self._spinner = IndeterminateProgressRing(self._card)
        self._spinner.setFixedSize(36, 36)
        self._spinner.setStrokeWidth(3)
        card_layout.addWidget(self._spinner, 0, Qt.AlignVCenter)

        # 文字列
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        self._label = QLabel(L("请稍候...", "Please wait..."), self._card)
        self._label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        font = QFont()
        font.setPointSize(11)
        self._label.setFont(font)
        text_col.addWidget(self._label)

        self._sub_label = QLabel("", self._card)
        self._sub_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        sub_font = QFont()
        sub_font.setPointSize(9)
        self._sub_label.setFont(sub_font)
        self._sub_label.setVisible(False)
        text_col.addWidget(self._sub_label)

        card_layout.addLayout(text_col, 1)

        # 监听主题变化
        qconfig.themeChanged.connect(self._apply_theme)

        # 初始应用主题
        self._apply_theme()

        # 初始隐藏
        self.hide()

    def _apply_theme(self):
        """根据当前主题应用对应的颜色方案。"""
        dark = isDarkTheme()

        if dark:
            # 深色主题
            card_bg = "rgba(32, 32, 32, 240)"
            card_border = "1px solid rgba(255, 255, 255, 0.08)"
            text_color = "rgb(245, 245, 245)"
            sub_text_color = "rgb(160, 165, 180)"
            self._shadow_color = QColor(0, 0, 0, 180)
            self._overlay_color = QColor(0, 0, 0, 90)
        else:
            # 浅色主题
            card_bg = "rgba(255, 255, 255, 245)"
            card_border = "1px solid rgba(0, 0, 0, 0.08)"
            text_color = "rgb(30, 30, 30)"
            sub_text_color = "rgb(110, 110, 120)"
            self._shadow_color = QColor(0, 0, 0, 80)
            self._overlay_color = QColor(0, 0, 0, 40)

        self._card.setStyleSheet(f"""
            #busyCard {{
                background-color: {card_bg};
                border-radius: 12px;
                border: {card_border};
            }}
        """)
        self._label.setStyleSheet(f"color: {text_color}; background: transparent;")
        self._sub_label.setStyleSheet(f"color: {sub_text_color}; background: transparent;")
        self._shadow.setColor(self._shadow_color)
        self.update()  # 触发重绘以更新遮罩颜色

    def show(self, text="", sub_text=""):
        """显示等待遮罩，覆盖整个父窗口。"""
        parent = self.parentWidget()
        if parent:
            self.setGeometry(0, 0, parent.width(), parent.height())
            if not self._event_filter_installed:
                parent.installEventFilter(self)
                self._event_filter_installed = True

        if text:
            self._label.setText(text)
        if sub_text:
            self._sub_label.setText(sub_text)
            self._sub_label.setVisible(True)
        else:
            self._sub_label.setVisible(False)

        self._spinner.start()
        self.raise_()
        super().show()
        self._position_card()
        QApplication.processEvents()

    def hide(self):
        """隐藏遮罩。"""
        self._spinner.stop()
        super().hide()

    def set_text(self, text, sub_text=""):
        """更新提示文字。"""
        self._label.setText(text)
        if sub_text:
            self._sub_label.setText(sub_text)
            self._sub_label.setVisible(True)
        QApplication.processEvents()

    def _position_card(self):
        """将卡片居中放置。"""
        self._card.adjustSize()
        cw = self._card.sizeHint().width()
        ch = self._card.sizeHint().height()
        x = (self.width() - cw) // 2
        y = (self.height() - ch) // 2
        self._card.move(max(0, x), max(0, y))

    def resizeEvent(self, event):
        """父窗口大小变化时重新定位卡片。"""
        super().resizeEvent(event)
        if self.isVisible():
            self._position_card()

    def eventFilter(self, obj, event):
        """父窗口大小变化时自动调整。"""
        if obj == self.parentWidget() and event.type() == QEvent.Resize:
            self.setGeometry(0, 0, self.parentWidget().width(), self.parentWidget().height())
            self._position_card()
        return super().eventFilter(obj, event)

    def paintEvent(self, event):
        """绘制半透明遮罩背景（颜色随主题变化）。"""
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), self._overlay_color)
        p.end()

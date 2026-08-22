# -*- coding: utf-8 -*-
"""NetPulse 幸运转盘插件：转一转，把选择交给运气。

内置 8 个趣味选项，可在「编辑选项」中改成自己的内容（每行一个，2-16 条）。
点击转盘中央的 GO 或「开始」按钮即可开转，结果实时显示并记录。
"""

import math
import random

from PySide6.QtCore import Qt, QRectF, QPointF, QVariantAnimation, QEasingCurve
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF, QFontMetricsF, QPalette
from PySide6.QtWidgets import QWidget

_COLORS = [
    "#e8595b", "#f3863a", "#f6bd3f", "#63ab4f",
    "#3795c9", "#546ee0", "#8a63d1", "#d561a8",
    "#4cb8a4", "#c9784e",
]


class _Wheel(QWidget):
    """转盘控件：绘制扇区与径向文字，负责旋转动画与结果计算。"""

    def __init__(self, options, on_finished, parent=None):
        super().__init__(parent)
        self._options = list(options)      # list[str]，外部保证 >= 2 项
        self._on_finished = on_finished    # 回调 (text: str)
        self._angle = 0.0                  # 当前旋转角度（度）
        self._anim = None
        self.setMinimumSize(380, 380)
        self.setCursor(Qt.PointingHandCursor)

    # ---------- 对外接口 ----------
    def set_options(self, options):
        self._options = list(options)
        self._angle = self._angle % 360.0
        self.update()

    def is_spinning(self):
        return self._anim is not None and self._anim.state() == QVariantAnimation.Running

    def spin(self):
        if self.is_spinning() or len(self._options) < 2:
            return
        n = len(self._options)
        seg = 360.0 / n
        # 目标扇区（随机），落点偏离扇区中心 ±0.35 扇区，避免每次都停在正中
        target = random.randrange(n)
        jitter = random.uniform(-0.35, 0.35)
        # 指针固定在正上方（90°）：使扇区 target 转到指针下所需的最终角度
        final = 90.0 - (target + 0.5 + jitter) * seg
        # 补足整圈，保证至少向前转 5 圈
        base = math.ceil((self._angle + 5 * 360.0 - final) / 360.0)
        final += base * 360.0

        anim = QVariantAnimation(self)
        anim.setStartValue(float(self._angle))
        anim.setEndValue(float(final))
        anim.setDuration(random.randint(3200, 4600))
        anim.setEasingCurve(QEasingCurve.OutQuint)
        anim.valueChanged.connect(self._set_angle)
        anim.finished.connect(lambda: self._finish(final))
        self._anim = anim
        anim.start()

    # ---------- 内部 ----------
    def _set_angle(self, v):
        self._angle = float(v)
        self.update()

    def _finish(self, final):
        self._anim = None
        self._angle = final % 360.0
        self.update()
        idx = self._winner_index(final)
        self._on_finished(self._options[idx])

    def _winner_index(self, angle):
        """指针（90°）指向的扇区索引。"""
        n = len(self._options)
        seg = 360.0 / n
        pos = (90.0 - angle) % 360.0
        return int(pos / seg) % n

    def mousePressEvent(self, ev):
        if ev.button() == Qt.LeftButton:
            self.spin()
        super().mousePressEvent(ev)

    # ---------- 绘制 ----------
    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        cx = self.width() / 2.0
        cy = self.height() / 2.0
        side = min(self.width(), self.height())
        r = side / 2.0 - 26  # 顶部留出指针位置

        n = len(self._options)
        seg = 360.0 / n

        # 金色外环
        p.setPen(Qt.NoPen)
        p.setBrush(QColor("#d9a441"))
        p.drawEllipse(QPointF(cx, cy), r + 7, r + 7)

        # 扇区
        p.save()
        p.translate(cx, cy)
        p.rotate(self._angle)
        for i in range(n):
            p.setBrush(QColor(_COLORS[i % len(_COLORS)]))
            p.setPen(QPen(QColor(255, 255, 255, 60), 1))
            p.drawPie(QRectF(-r, -r, 2 * r, 2 * r),
                      int(i * seg * 16), int(seg * 16))
        # 径向文字（左半侧翻转 180°，保证文字始终正向可读）
        f = QFont(self.font())
        f.setBold(True)
        f.setPixelSize(max(12, int(r * 0.105)))
        p.setFont(f)
        for i, text in enumerate(self._options):
            p.save()
            p.rotate(i * seg + seg / 2.0)
            mid = (i * seg + seg / 2.0 + self._angle) % 360.0
            m = QFontMetricsF(f)
            maxw = r * 0.60
            if m.horizontalAdvance(text) > maxw:
                text = m.elidedText(text, Qt.ElideRight, maxw)
            if 90.0 < mid < 270.0:
                p.rotate(180)
                rect = QRectF(-r * 0.92, -r * 0.115, maxw, r * 0.23)
                flags = Qt.AlignRight | Qt.AlignVCenter
            else:
                rect = QRectF(r * 0.32, -r * 0.115, maxw, r * 0.23)
                flags = Qt.AlignLeft | Qt.AlignVCenter
            p.setPen(QColor("white"))
            p.drawText(rect, flags, text)
            p.restore()
        p.restore()

        # 中央按钮（GO）
        hub = r * 0.16
        p.setBrush(self.palette().color(QPalette.Window))
        p.setPen(QPen(QColor("#d9a441"), 3))
        p.drawEllipse(QPointF(cx, cy), hub, hub)
        hf = QFont(self.font())
        hf.setBold(True)
        hf.setPixelSize(max(14, int(r * 0.09)))
        p.setFont(hf)
        p.setPen(self.palette().color(QPalette.WindowText))
        p.drawText(QRectF(cx - hub, cy - hub, 2 * hub, 2 * hub),
                   Qt.AlignCenter, "GO")

        # 顶部指针
        p.setPen(QPen(QColor("white"), 2))
        p.setBrush(QColor("#e02b2e"))
        p.drawPolygon(QPolygonF([
            QPointF(cx - 12, cy - r - 16),
            QPointF(cx + 12, cy - r - 16),
            QPointF(cx, cy - r + 10),
        ]))


class Plugin(NetPulsePlugin):
    name = ("幸运转盘", "Lucky Wheel")
    version = "1.0"
    author = "NetPulse"
    description = ("转一转，随机帮你做决定：内置趣味选项，支持自定义，一键开转。",
                   "Let luck decide: fun preset options, fully customizable, one click to spin.")
    icon = "lucky_wheel.png"   # 图片路径（相对本插件文件）
    category = "other"

    _DEFAULTS = [
        ("喝一杯奶茶", "Bubble tea"),
        ("看一场电影", "Movie night"),
        ("睡个懒觉", "Sleep in"),
        ("打一局游戏", "Gaming time"),
        ("吃顿好的", "Nice dinner"),
        ("散步半小时", "A short walk"),
        ("再转一次", "Spin again"),
        ("谢谢参与", "Thanks anyway"),
    ]

    def on_load(self, ctx):
        self._ctx = ctx
        self._options = [ctx.tr(zh, en) for zh, en in self._DEFAULTS]
        self._history = []

    # ---------- 页面 ----------
    def create_widget(self, parent):
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout
        from qfluentwidgets import (SubtitleLabel, TitleLabel, BodyLabel, CaptionLabel,
                                    PrimaryPushButton, PushButton, SimpleCardWidget,
                                    TextEdit, MessageBoxBase, InfoBar)

        tr = self._ctx.tr

        class _EditDialog(MessageBoxBase):
            """编辑选项对话框：每行一个选项。"""

            def __init__(self, parent, text):
                super().__init__(parent)
                # 注意：本版本 qfluentwidgets 的 MessageBoxBase 无 titleLabel，
                # 标题需自行加入 viewLayout
                self.viewLayout.addWidget(SubtitleLabel(tr("编辑选项", "Edit options")))
                self.viewLayout.addWidget(CaptionLabel(tr(
                    "每行一个选项，至少 2 条，最多 16 条。",
                    "One option per line, 2 to 16 lines.")))
                self.edit = TextEdit(self)
                self.edit.setPlainText(text)
                self.edit.setFixedHeight(240)
                self.viewLayout.addWidget(self.edit)
                self.cancelButton.setText(tr("取消", "Cancel"))
                self.yesButton.setText(tr("保存", "Save"))

            def result(self):
                return [ln.strip() for ln in self.edit.toPlainText().splitlines()
                        if ln.strip()]

        w = QWidget(parent)
        lay = QVBoxLayout(w)
        lay.setContentsMargins(36, 24, 36, 24)
        lay.setSpacing(10)

        lay.addWidget(SubtitleLabel(tr("幸运转盘", "Lucky Wheel")))

        # 结果标题
        self._result = TitleLabel(tr("点击 GO 开始", "Click GO to spin"))
        self._result.setAlignment(Qt.AlignCenter)
        lay.addWidget(self._result)

        # 转盘
        self._wheel = _Wheel(self._options, self._on_result, w)
        lay.addWidget(self._wheel, 1, Qt.AlignCenter)

        # 按钮行
        row = QHBoxLayout()
        row.setSpacing(12)
        self._spin_btn = PrimaryPushButton(tr("开始", "Spin"))
        self._spin_btn.setFixedWidth(140)
        self._spin_btn.clicked.connect(self._wheel.spin)
        edit_btn = PushButton(tr("编辑选项", "Edit options"))
        edit_btn.setFixedWidth(140)

        def open_edit():
            if self._wheel.is_spinning():
                return
            dlg = _EditDialog(w, "\n".join(self._options))
            if dlg.exec():
                items = dlg.result()
                if not 2 <= len(items) <= 16:
                    InfoBar.warning(tr("选项数量不合适", "Invalid option count"),
                                    tr("至少 2 条，最多 16 条。", "Use 2 to 16 lines."),
                                    parent=w, duration=3000)
                    return
                self._options = items
                self._wheel.set_options(items)

        edit_btn.clicked.connect(open_edit)
        row.addStretch(1)
        row.addWidget(self._spin_btn)
        row.addWidget(edit_btn)
        row.addStretch(1)
        lay.addLayout(row)

        # 结果记录卡片
        card = SimpleCardWidget(w)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 14, 20, 14)
        cl.setSpacing(6)
        cl.addWidget(CaptionLabel(tr("结果记录（最近 10 次）", "Results (last 10)")))
        self._history_label = BodyLabel(tr("暂无记录", "No results yet"))
        self._history_label.setWordWrap(True)
        cl.addWidget(self._history_label)
        lay.addWidget(card)

        return w

    # ---------- 结果回调 ----------
    def _on_result(self, text):
        from app.ui.i18n import current_lang

        def tr(zh, en):
            return zh if current_lang() == "zh-CN" else en

        self._result.setText(tr("结果：", "Result: ") + text)
        self._history.insert(0, text)
        del self._history[10:]
        self._history_label.setText("  ·  ".join(self._history))

    def on_unload(self):
        pass

"""主页：欢迎区 + 快速开始 + 系统资源卡片 + 实时曲线。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)
import pyqtgraph as pg
from qfluentwidgets import (BodyLabel, CaptionLabel, PrimaryPushButton,
                            ScrollArea, SimpleCardWidget,
                            StrongBodyLabel, TitleLabel)

from app.services.monitor import monitor
from app.ui.charts import ACCENT, GREEN, PURPLE, HoverChart
from app.ui.i18n import L


class StatCard(SimpleCardWidget):
    def __init__(self, title, unit="", color=ACCENT, parent=None):
        super().__init__(parent)
        self.title = QLabel(title, self)
        self.title.setStyleSheet("font-size:16px; font-weight:600; color:#888; background:transparent;")
        self.value = QLabel("--", self)
        self.unit = QLabel(unit, self)
        self.unit.setStyleSheet("font-size:13px; color:#999; background:transparent;")
        self.value.setStyleSheet(
            f"font-size:34px; font-weight:700; color:{color}; background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 18)
        lay.setSpacing(8)
        lay.addWidget(self.title)
        lay.addWidget(self.value)
        lay.addWidget(self.unit)
        lay.addStretch(1)
        self.setMinimumHeight(130)

    def set_value(self, text):
        self.value.setText(text)


class DashboardView(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("dashboardView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        # 标题区
        title_row = QHBoxLayout()
        tcol = QVBoxLayout()
        self.titleLabel = TitleLabel("NetPulse", self.view)
        self.subLabel = CaptionLabel(
            L("合法授权网络压力测试与性能监控工具", "Authorized Network Stress Testing & Performance Monitoring"), self.view)
        tcol.addWidget(self.titleLabel)
        tcol.addWidget(self.subLabel)
        title_row.addLayout(tcol)
        title_row.addStretch(1)
        root.addLayout(title_row)

        # 快速开始卡片
        quick = SimpleCardWidget(self.view)
        ql = QHBoxLayout(quick)
        ql.setContentsMargins(20, 16, 20, 16)
        qcol = QVBoxLayout()
        qt = StrongBodyLabel(L("快速开始", "Quick Start"), quick)
        qs = BodyLabel(L("配置目标 → 确认授权 → 开始测试", "Configure target → Confirm authorization → Start"), quick)
        qcol.addWidget(qt)
        qcol.addWidget(qs)
        ql.addLayout(qcol)
        ql.addStretch(1)
        self.quickBtn = PrimaryPushButton(L("开始压力测试", "Start Stress Test"), quick)
        self.quickBtn.clicked.connect(lambda: self.window().go_stress())
        ql.addWidget(self.quickBtn)
        root.addWidget(quick)

        # 资源统计卡片
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.cardCpu = StatCard(L("CPU 使用率", "CPU Usage"), "", ACCENT)
        self.cardMem = StatCard(L("内存使用率", "Memory Usage"), "", PURPLE)
        self.cardDown = StatCard(L("下行速率", "Download"), "KB/s", GREEN)
        self.cardUp = StatCard(L("上行速率", "Upload"), "KB/s", ACCENT)
        grid.addWidget(self.cardCpu, 0, 0)
        grid.addWidget(self.cardMem, 0, 1)
        grid.addWidget(self.cardDown, 1, 0)
        grid.addWidget(self.cardUp, 1, 1)
        root.addLayout(grid)

        # 实时曲线卡片
        chart_card = SimpleCardWidget(self.view)
        cl = QVBoxLayout(chart_card)
        cl.setContentsMargins(20, 16, 20, 12)
        ct = StrongBodyLabel(L("系统资源趋势", "System Resource Trend"), chart_card)
        cl.addWidget(ct)
        self.plot = HoverChart(window_points=60, y_min=0.0)
        self.plot.addLegend(offset=(8, 8))
        self.plot.add_series(L("CPU %", "CPU %"), ACCENT, " %")
        self.plot.add_series(L("内存 %", "Memory %"), PURPLE, " %")
        cl.addWidget(self.plot, 1)
        root.addWidget(chart_card, 1)

        self._cpu_hist, self._mem_hist = [], []
        monitor.updated.connect(self._on_update)

    def _on_update(self, d):
        self.cardCpu.set_value(f"{d['cpu']:.1f} %")
        self.cardMem.set_value(f"{d['mem_percent']:.1f} %")
        self.cardDown.set_value(f"{d['down_kbs']:.1f}")
        self.cardUp.set_value(f"{d['up_kbs']:.1f}")
        self._cpu_hist.append(float(d["cpu"]))
        self._mem_hist.append(float(d["mem_percent"]))
        self._cpu_hist = self._cpu_hist[-60:]
        self._mem_hist = self._mem_hist[-60:]
        self.plot.set_data({
            L("CPU %", "CPU %"): self._cpu_hist,
            L("内存 %", "Memory %"): self._mem_hist,
        })

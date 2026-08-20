"""主页：欢迎区 + 快速开始 + 系统资源卡片（带进度条）+ 实时曲线。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget, QProgressBar)
from qfluentwidgets import (BodyLabel, CaptionLabel, PrimaryPushButton,
                            ScrollArea, SimpleCardWidget,
                            StrongBodyLabel, TitleLabel, isDarkTheme, qconfig)

from app.services.monitor import monitor
from app.ui.charts import ACCENT, GREEN, PURPLE, HoverChart
from app.ui.i18n import L


def _usage_color(pct: float) -> str:
    """根据使用率返回进度条颜色（绿→黄→红）。"""
    if pct < 60:
        return "#107C10"   # 绿色
    elif pct < 85:
        return "#F2B010"  # 黄色
    else:
        return "#D13438"   # 红色


def _bar_bg_color() -> str:
    """进度条轨道背景色，根据主题返回。"""
    if isDarkTheme():
        return "rgba(255,255,255,0.08)"
    else:
        return "rgba(0,0,0,0.06)"


def _subtle_text_color() -> str:
    """次要文字颜色，根据主题返回。"""
    if isDarkTheme():
        return "#999"
    else:
        return "#8A8A8A"


def _title_text_color() -> str:
    """标题次文字颜色，根据主题返回。"""
    if isDarkTheme():
        return "#888"
    else:
        return "#6E6E6E"


class StatCard(SimpleCardWidget):
    """普通统计卡片（用于网络速率等无百分比的指标）。"""

    def __init__(self, title, unit="", color=ACCENT, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(6)
        # 标题 - 使用 qfluentwidgets 的 CaptionLabel 自动适配主题
        self.titleLabel = CaptionLabel(title, self)
        lay.addWidget(self.titleLabel)
        # 大数值 - 用 QLabel 但设置显眼的颜色（在两种主题下都可见）
        self.value = QLabel("--", self)
        self.value.setStyleSheet(
            f"font-size:32px; font-weight:700; color:{color}; background:transparent;")
        lay.addWidget(self.value)
        # 单位
        self.unit = QLabel(unit, self)
        self.unit.setStyleSheet(
            f"font-size:12px; color:{_subtle_text_color()}; background:transparent;")
        lay.addWidget(self.unit)
        lay.addStretch(1)
        self.setMinimumHeight(120)
        # 主题切换时刷新次要文字颜色（初始化时写死会残留旧主题的颜色）
        qconfig.themeChanged.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self, *_):
        self.unit.setStyleSheet(
            f"font-size:12px; color:{_subtle_text_color()}; background:transparent;")

    def set_value(self, text):
        self.value.setText(text)


class PercentCard(SimpleCardWidget):
    """带进度条的百分比卡片（CPU / 内存专用）。"""

    def __init__(self, title, color=ACCENT, parent=None):
        super().__init__(parent)
        self._base_color = color
        self._cur_color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(8)

        # 标题
        self.titleLabel = CaptionLabel(title, self)
        lay.addWidget(self.titleLabel)

        # 大百分比数字
        self.valueLabel = QLabel("-- %", self)
        self.valueLabel.setStyleSheet(
            f"font-size:36px; font-weight:700; color:{color}; background:transparent;")
        lay.addWidget(self.valueLabel)

        # 进度条
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self._apply_bar_style(color)
        lay.addWidget(self.bar)

        # 详细信息
        self.detailLabel = QLabel("", self)
        self.detailLabel.setStyleSheet(
            f"font-size:12px; color:{_subtle_text_color()}; background:transparent;")
        lay.addWidget(self.detailLabel)

        lay.addStretch(1)
        self.setMinimumHeight(150)
        # 主题切换时刷新次要文字颜色（初始化时写死会残留旧主题的颜色）
        qconfig.themeChanged.connect(self._refresh_theme_colors)

    def _refresh_theme_colors(self, *_):
        self.detailLabel.setStyleSheet(
            f"font-size:12px; color:{_subtle_text_color()}; background:transparent;")
        self._apply_bar_style(self._cur_color)

    def _apply_bar_style(self, color: str):
        bg = _bar_bg_color()
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {bg};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                border-radius: 3px;
                background-color: {color};
            }}
        """)

    def set_percent(self, pct: float, detail: str = ""):
        """设置百分比（0-100）和详情文字。"""
        pct = max(0.0, min(100.0, pct))
        c = _usage_color(pct)
        self._cur_color = c
        self.valueLabel.setText(f"{pct:.1f} %")
        self.valueLabel.setStyleSheet(
            f"font-size:36px; font-weight:700; color:{c}; background:transparent;")
        self.bar.setValue(int(round(pct)))
        self._apply_bar_style(c)
        if detail:
            self.detailLabel.setText(detail)
            self.detailLabel.setVisible(True)
        else:
            self.detailLabel.setVisible(False)


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

        # 资源统计卡片（CPU、内存用 PercentCard，网络用普通 StatCard）
        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.cardCpu = PercentCard(L("CPU 使用率", "CPU Usage"), ACCENT)
        self.cardMem = PercentCard(L("内存使用率", "Memory Usage"), PURPLE)
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
        cpu = float(d["cpu"])
        mem_pct = float(d["mem_percent"])
        mem_used = float(d["mem_used_gb"])
        mem_total = float(d["mem_total_gb"])
        mem_free = mem_total - mem_used

        # CPU 卡片
        self.cardCpu.set_percent(cpu, L(
            f"剩余 {100 - cpu:.1f}% 可用",
            f"{100 - cpu:.1f}% available"
        ))

        # 内存卡片
        self.cardMem.set_percent(mem_pct, L(
            f"{mem_used:.1f} / {mem_total:.1f} GB  剩余 {mem_free:.1f} GB",
            f"{mem_used:.1f} / {mem_total:.1f} GB  {mem_free:.1f} GB free"
        ))

        # 网络速率
        self.cardDown.set_value(f"{d['down_kbs']:.1f}")
        self.cardUp.set_value(f"{d['up_kbs']:.1f}")

        self._cpu_hist.append(cpu)
        self._mem_hist.append(mem_pct)
        self._cpu_hist = self._cpu_hist[-60:]
        self._mem_hist = self._mem_hist[-60:]
        self.plot.set_data({
            L("CPU %", "CPU %"): self._cpu_hist,
            L("内存 %", "Memory %"): self._mem_hist,
        })

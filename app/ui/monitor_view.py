"""监控面板：资源卡片（带进度条）+ CPU/内存曲线 + 网络速率曲线。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QLabel,
                               QVBoxLayout, QWidget, QProgressBar)
from qfluentwidgets import (CaptionLabel, ScrollArea, SimpleCardWidget,
                            StrongBodyLabel, SubtitleLabel, isDarkTheme)

from app.services.monitor import monitor
from app.ui.charts import ACCENT, GREEN, PURPLE, HoverChart
from app.ui.i18n import L

WINDOW_POINTS = 60  # 最近 60 个采样点（约 1 分钟，每秒一次）


def _usage_color(pct: float) -> str:
    if pct < 60:
        return "#107C10"
    elif pct < 85:
        return "#F2B010"
    else:
        return "#D13438"


def _bar_bg_color() -> str:
    if isDarkTheme():
        return "rgba(255,255,255,0.08)"
    else:
        return "rgba(0,0,0,0.06)"


def _subtle_text_color() -> str:
    if isDarkTheme():
        return "#999"
    else:
        return "#8A8A8A"


class StatTile(SimpleCardWidget):
    """普通统计卡片（用于 TCP 连接数、进程数等）。"""

    def __init__(self, title, color=ACCENT, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(6)
        # 标题 - 使用 qfluentwidgets 的 CaptionLabel 自动适配主题
        self.titleLabel = CaptionLabel(title, self)
        lay.addWidget(self.titleLabel)
        # 大数值
        self.value = QLabel("--")
        self.value.setStyleSheet(f"font-size:32px; font-weight:700; color:{color}; background:transparent;")
        lay.addWidget(self.value)
        lay.addStretch(1)
        self.setMinimumHeight(120)

    def set(self, text):
        self.value.setText(text)


class PercentTile(SimpleCardWidget):
    """带进度条的百分比卡片（CPU / 内存专用）。"""

    def __init__(self, title, color=ACCENT, parent=None):
        super().__init__(parent)
        self._base_color = color
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 20, 24, 18)
        lay.setSpacing(8)

        self.titleLabel = CaptionLabel(title, self)
        lay.addWidget(self.titleLabel)

        self.valueLabel = QLabel("-- %", self)
        self.valueLabel.setStyleSheet(
            f"font-size:36px; font-weight:700; color:{color}; background:transparent;")
        lay.addWidget(self.valueLabel)

        self.bar = QProgressBar(self)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        self._apply_bar_style(color)
        lay.addWidget(self.bar)

        self.detailLabel = QLabel("", self)
        self.detailLabel.setStyleSheet(
            f"font-size:12px; color:{_subtle_text_color()}; background:transparent;")
        lay.addWidget(self.detailLabel)

        lay.addStretch(1)
        self.setMinimumHeight(150)

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
        pct = max(0.0, min(100.0, pct))
        c = _usage_color(pct)
        self.valueLabel.setText(f"{pct:.1f} %")
        self.valueLabel.setStyleSheet(
            f"font-size:36px; font-weight:700; color:{c}; background:transparent;")
        self.bar.setValue(int(round(pct)))
        self._apply_bar_style(c)
        self.detailLabel.setText(detail)
        self.detailLabel.setVisible(bool(detail))


class MonitorView(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("monitorView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)
        root.addWidget(SubtitleLabel(L("监控面板", "Monitor"), self.view))

        grid = QGridLayout()
        grid.setSpacing(12)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        self.tCpu = PercentTile(L("CPU 使用率", "CPU Usage"), ACCENT)
        self.tMem = PercentTile(L("内存", "Memory"), PURPLE)
        self.tTcp = StatTile(L("TCP 连接数", "TCP Connections"), GREEN)
        self.tProc = StatTile(L("进程数", "Processes"), ACCENT)
        grid.addWidget(self.tCpu, 0, 0)
        grid.addWidget(self.tMem, 0, 1)
        grid.addWidget(self.tTcp, 1, 0)
        grid.addWidget(self.tProc, 1, 1)
        root.addLayout(grid)

        # CPU / 内存：百分比 0-100，Y 轴下限固定为 0
        cpu_card = SimpleCardWidget(self.view)
        cl = QVBoxLayout(cpu_card)
        cl.setContentsMargins(20, 16, 20, 12)
        cl.addWidget(StrongBodyLabel(L("CPU / 内存趋势", "CPU / Memory Trend"), cpu_card))
        self.cpuPlot = HoverChart(window_points=WINDOW_POINTS, y_min=0.0)
        self.cpuPlot.addLegend(offset=(8, 8))
        self.cpuPlot.add_series(L("CPU %", "CPU %"), ACCENT, " %")
        self.cpuPlot.add_series(L("内存 %", "Memory %"), PURPLE, " %")
        cl.addWidget(self.cpuPlot, 1)
        root.addWidget(cpu_card, 1)

        # 网络速率：非负值，Y 轴自动适配
        net_card = SimpleCardWidget(self.view)
        nl = QVBoxLayout(net_card)
        nl.setContentsMargins(20, 16, 20, 12)
        nl.addWidget(StrongBodyLabel(L("网络速率", "Network Throughput"), net_card))
        self.netPlot = HoverChart(window_points=WINDOW_POINTS, y_min=0.0)
        self.netPlot.addLegend(offset=(8, 8))
        self.netPlot.add_series(L("下行 KB/s", "Download KB/s"), ACCENT, " KB/s")
        self.netPlot.add_series(L("上行 KB/s", "Upload KB/s"), GREEN, " KB/s")
        nl.addWidget(self.netPlot, 1)
        root.addWidget(net_card, 1)

        self._cpu: list[float] = []
        self._mem: list[float] = []
        self._down: list[float] = []
        self._up: list[float] = []

        monitor.updated.connect(self._on_update)

    def _on_update(self, d):
        cpu = float(d["cpu"])
        mem_pct = float(d["mem_percent"])
        mem_used = float(d["mem_used_gb"])
        mem_total = float(d["mem_total_gb"])
        mem_free = mem_total - mem_used

        self.tCpu.set_percent(cpu, L(
            f"剩余 {100 - cpu:.1f}% 可用",
            f"{100 - cpu:.1f}% available"
        ))
        self.tMem.set_percent(mem_pct, L(
            f"{mem_used:.1f} / {mem_total:.1f} GB  剩余 {mem_free:.1f} GB",
            f"{mem_used:.1f} / {mem_total:.1f} GB  {mem_free:.1f} GB free"
        ))
        self.tTcp.set(str(d["tcp_conns"]) if d["tcp_conns"] >= 0 else L("无权限", "N/A"))
        try:
            import psutil
            self.tProc.set(str(len(psutil.pids())))
        except Exception:
            self.tProc.set("--")

        self._cpu.append(cpu)
        self._mem.append(mem_pct)
        self._down.append(float(d["down_kbs"]))
        self._up.append(float(d["up_kbs"]))
        self._cpu = self._cpu[-WINDOW_POINTS:]
        self._mem = self._mem[-WINDOW_POINTS:]
        self._down = self._down[-WINDOW_POINTS:]
        self._up = self._up[-WINDOW_POINTS:]

        self.cpuPlot.set_data({
            L("CPU %", "CPU %"): self._cpu,
            L("内存 %", "Memory %"): self._mem,
        })
        self.netPlot.set_data({
            L("下行 KB/s", "Download KB/s"): self._down,
            L("上行 KB/s", "Upload KB/s"): self._up,
        })

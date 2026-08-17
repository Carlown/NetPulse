"""监控面板：资源卡片 + CPU/内存曲线 + 网络速率曲线。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (ScrollArea, SimpleCardWidget,
                            StrongBodyLabel, SubtitleLabel)

from app.services.monitor import monitor
from app.ui.charts import ACCENT, GREEN, PURPLE, HoverChart
from app.ui.i18n import L

WINDOW_POINTS = 60  # 最近 60 个采样点（约 1 分钟，每秒一次）


class StatTile(SimpleCardWidget):
    def __init__(self, title, color=ACCENT, parent=None):
        super().__init__(parent)
        self.value = QLabel("--")
        self.value.setStyleSheet(f"font-size:34px; font-weight:700; color:{color}; background:transparent;")
        self.title = QLabel(title, self)
        self.title.setStyleSheet("font-size:16px; font-weight:600; color:#888; background:transparent;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(26, 22, 26, 20)
        lay.setSpacing(8)
        lay.addWidget(self.title)
        lay.addWidget(self.value)
        lay.addStretch(1)
        self.setMinimumHeight(118)

    def set(self, text):
        self.value.setText(text)


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
        self.tCpu = StatTile(L("CPU 使用率", "CPU Usage"), ACCENT)
        self.tMem = StatTile(L("内存", "Memory"), PURPLE)
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
        self.tCpu.set(f"{d['cpu']:.1f} %")
        self.tMem.set(f"{d['mem_percent']:.1f} %  ({d['mem_used_gb']:.1f}/{d['mem_total_gb']:.1f} GB)")
        self.tTcp.set(str(d["tcp_conns"]) if d["tcp_conns"] >= 0 else L("无权限", "N/A"))
        try:
            import psutil
            self.tProc.set(str(len(psutil.pids())))
        except Exception:
            self.tProc.set("--")

        self._cpu.append(float(d["cpu"]))
        self._mem.append(float(d["mem_percent"]))
        self._down.append(float(d["down_kbs"]))
        self._up.append(float(d["up_kbs"]))
        # 只保留窗口大小
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

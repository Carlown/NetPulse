"""监控面板：资源卡片、可暂停实时曲线与采样历史导出。"""
import csv
from collections import deque
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QProgressBar, QVBoxLayout, QWidget)
from qfluentwidgets import (CaptionLabel, ComboBox, InfoBar, PushButton,
                            ScrollArea, SimpleCardWidget, StrongBodyLabel,
                            SubtitleLabel, isDarkTheme, qconfig)

from app.services.monitor import monitor
from app.ui.charts import ACCENT, GREEN, PURPLE, HoverChart
from app.ui.i18n import L

WINDOW_POINTS = 60  # 最近 60 个采样点（约 1 分钟，每秒一次）
MAX_WINDOW_POINTS = 900
WINDOW_OPTIONS = (60, 300, 900)
CSV_FIELDS = (
    "timestamp", "cpu_percent", "memory_percent", "memory_used_gb",
    "memory_total_gb", "download_kbs", "upload_kbs", "tcp_connections",
    "process_count",
)


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
        self._cur_color = color
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
        # 主题切换时刷新次要文字颜色与进度条轨道（初始化时写死会残留旧主题的颜色）
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
        pct = max(0.0, min(100.0, pct))
        c = _usage_color(pct)
        self._cur_color = c
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
        self._samples = deque(maxlen=MAX_WINDOW_POINTS)
        self._window_points = WINDOW_POINTS
        self._plot_paused = False
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        # 标题与实时曲线工具栏
        header = QHBoxLayout()
        header.setSpacing(8)
        header.addWidget(SubtitleLabel(L("监控面板", "Monitor"), self.view))
        header.addStretch(1)
        header.addWidget(CaptionLabel(L("时间窗", "Window"), self.view))
        self.windowCombo = ComboBox(self.view)
        self.windowCombo.addItems([
            L("1 分钟", "1 min"), L("5 分钟", "5 min"), L("15 分钟", "15 min")
        ])
        self.windowCombo.setCurrentIndex(0)
        self.windowCombo.setMinimumWidth(92)
        self.windowCombo.currentIndexChanged.connect(self._on_window_changed)
        header.addWidget(self.windowCombo)
        self.pauseBtn = PushButton(L("暂停绘图", "Pause Charts"), self.view)
        self.pauseBtn.clicked.connect(self._toggle_plot_pause)
        header.addWidget(self.pauseBtn)
        self.clearBtn = PushButton(L("清空历史", "Clear History"), self.view)
        self.clearBtn.clicked.connect(self._clear_history)
        header.addWidget(self.clearBtn)
        self.exportBtn = PushButton(L("导出 CSV", "Export CSV"), self.view)
        self.exportBtn.clicked.connect(self._export_csv)
        header.addWidget(self.exportBtn)
        root.addLayout(header)

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
        self._cpu_name = L("CPU %", "CPU %")
        self._mem_name = L("内存 %", "Memory %")
        self.cpuPlot.add_series(self._cpu_name, ACCENT, " %")
        self.cpuPlot.add_series(self._mem_name, PURPLE, " %")
        cl.addWidget(self.cpuPlot, 1)
        root.addWidget(cpu_card, 1)

        # 网络速率：非负值，Y 轴自动适配
        net_card = SimpleCardWidget(self.view)
        nl = QVBoxLayout(net_card)
        nl.setContentsMargins(20, 16, 20, 12)
        nl.addWidget(StrongBodyLabel(L("网络速率", "Network Throughput"), net_card))
        self.netPlot = HoverChart(window_points=WINDOW_POINTS, y_min=0.0)
        self.netPlot.addLegend(offset=(8, 8))
        self._down_name = L("下行 KB/s", "Download KB/s")
        self._up_name = L("上行 KB/s", "Upload KB/s")
        self.netPlot.add_series(self._down_name, ACCENT, " KB/s")
        self.netPlot.add_series(self._up_name, GREEN, " KB/s")
        nl.addWidget(self.netPlot, 1)
        root.addWidget(net_card, 1)

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
        tcp_conns = int(d["tcp_conns"])
        self.tTcp.set(str(tcp_conns) if tcp_conns >= 0 else L("无权限", "N/A"))
        try:
            import psutil
            process_count = len(psutil.pids())
        except Exception:
            process_count = -1
        self.tProc.set(str(process_count) if process_count >= 0 else "--")

        # 无论曲线是否暂停，采样都持续写入固定长度缓存。
        self._samples.append({
            "timestamp": datetime.now().astimezone().isoformat(timespec="seconds"),
            "cpu_percent": cpu,
            "memory_percent": mem_pct,
            "memory_used_gb": mem_used,
            "memory_total_gb": mem_total,
            "download_kbs": float(d["down_kbs"]),
            "upload_kbs": float(d["up_kbs"]),
            "tcp_connections": tcp_conns,
            "process_count": process_count,
        })
        if not self._plot_paused:
            self._refresh_plots()

    def _refresh_plots(self):
        samples = list(self._samples)[-self._window_points:]
        self.cpuPlot.set_data({
            self._cpu_name: [s["cpu_percent"] for s in samples],
            self._mem_name: [s["memory_percent"] for s in samples],
        })
        self.netPlot.set_data({
            self._down_name: [s["download_kbs"] for s in samples],
            self._up_name: [s["upload_kbs"] for s in samples],
        })

    def _toggle_plot_pause(self):
        self._plot_paused = not self._plot_paused
        self.pauseBtn.setText(
            L("继续绘图", "Resume Charts") if self._plot_paused
            else L("暂停绘图", "Pause Charts")
        )
        if not self._plot_paused:
            self._refresh_plots()

    def _clear_history(self):
        self._samples.clear()
        # 清空同时退出手动缩放，确保下一条采样能立即重新出现在视野中。
        self.cpuPlot.set_window_points(self._window_points)
        self.netPlot.set_window_points(self._window_points)
        self.cpuPlot.set_data({self._cpu_name: [], self._mem_name: []})
        self.netPlot.set_data({self._down_name: [], self._up_name: []})

    def _on_window_changed(self, index: int):
        if not 0 <= index < len(WINDOW_OPTIONS):
            return
        self._window_points = WINDOW_OPTIONS[index]
        self.cpuPlot.set_window_points(self._window_points)
        self.netPlot.set_window_points(self._window_points)
        # 直接操作时间窗应立即生效；暂停只阻止后台采样触发重绘。
        self._refresh_plots()

    def _export_csv(self):
        samples = list(self._samples)
        if not samples:
            InfoBar.warning(
                L("暂无数据", "No data"),
                L("当前没有可导出的监控历史", "There is no monitoring history to export"),
                parent=self.window(),
            )
            return
        default_name = "netpulse-monitor-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".csv"
        path, _ = QFileDialog.getSaveFileName(
            self, L("导出监控数据", "Export monitoring data"), default_name,
            L("CSV 文件 (*.csv)", "CSV files (*.csv)"),
        )
        if not path:
            return
        if not path.lower().endswith(".csv"):
            path += ".csv"
        try:
            with open(path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
                writer.writeheader()
                writer.writerows(samples)
            InfoBar.success(
                L("导出成功", "Exported"),
                L(f"已导出 {len(samples)} 条监控记录", f"Exported {len(samples)} monitoring samples"),
                parent=self.window(),
            )
        except Exception as e:
            InfoBar.error(
                L("导出失败", "Export failed"), str(e), parent=self.window()
            )

"""压力测试页：左侧配置 + 右侧实时统计与报告。"""
import json
import time as _time

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, InfoBar,
                            InfoBarPosition, MessageBox,
                            PrimaryPushButton, ProgressBar, PushButton,
                            ScrollArea, SimpleCardWidget, Slider, SpinBox,
                            StrongBodyLabel, SubtitleLabel, TextEdit,
                            isDarkTheme)

from app.services.auth import add_authorized, is_authorized, normalize_host
from app.services.logger import log
from app.services.settings import settings
from app.services.stress import engine
from app.ui.disclaimer import AuthDialog
from app.ui.i18n import L

HIGH_RATE = 500  # 高速率二次确认阈值
CONFIG_VERSION = 1  # 配置文件格式版本，用于将来兼容

# 错误码 -> 双语文案（引擎只存错误码，这里按当前语言翻译）
_ERR_TEXT = {
    "timeout": ("超时", "Timeout"),
    "refused": ("连接被拒", "Connection refused"),
    "reset": ("连接被重置", "Connection reset"),
    "unreachable": ("网络不可达", "Unreachable"),
    "dns": ("DNS 解析失败", "DNS resolution failed"),
    "tls": ("TLS 握手失败", "TLS handshake failed"),
    "cert": ("证书错误", "Certificate error"),
    "closed": ("连接已关闭", "Connection closed"),
    "conn": ("连接错误", "Connection error"),
    "icmp_dead": ("ICMP 无响应", "ICMP no reply"),
}


def err_text(code: str) -> str:
    """把引擎错误码翻译成当前语言的文案。HTTP 状态码等原样显示。"""
    pair = _ERR_TEXT.get(code)
    if pair:
        return L(pair[0], pair[1])
    if code.startswith("errno_"):
        return L(f"系统错误 {code[6:]}", f"OS error {code[6:]}")
    return code


_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def fmt_bytes(n: float) -> str:
    """字节数转人类可读单位：B → KB → MB → GB → TB → PB。"""
    n = float(n or 0)
    for u in _UNITS:
        if n < 1024 or u == _UNITS[-1]:
            return f"{n:.2f} {u}" if u != "B" else f"{int(n)} B"
        n /= 1024
    return f"{n:.2f} PB"


def _subtle_text_color() -> str:
    """次要文字颜色，根据主题返回。"""
    if isDarkTheme():
        return "#AAAAAA"
    else:
        return "#666666"


class MiniStat(QLabel):
    def __init__(self, color, parent=None):
        super().__init__("--", parent)
        self.setStyleSheet(f"font-size:22px; font-weight:600; color:{color}; background:transparent;")


class StressView(ScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("stressView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        self.titleLabel = SubtitleLabel(L("压力测试", "Stress Test"), self.view)
        root.addWidget(self.titleLabel)

        cols = QHBoxLayout()
        cols.setSpacing(16)
        cols.addWidget(self._build_config_card(), 5)
        cols.addWidget(self._build_stats_card(), 6)
        root.addLayout(cols)

        # 报告卡片
        self.reportCard = SimpleCardWidget(self.view)
        rl = QVBoxLayout(self.reportCard)
        rl.setContentsMargins(20, 16, 20, 14)
        rl.addWidget(StrongBodyLabel(L("汇总报告", "Summary Report"), self.reportCard))
        self.reportLabel = BodyLabel(L("尚未执行测试。", "No test executed yet."), self.reportCard)
        self.reportLabel.setWordWrap(True)
        rl.addWidget(self.reportLabel)
        root.addWidget(self.reportCard)

        root.addStretch(1)

        engine.snapshot.connect(self._on_snapshot)
        engine.report_ready.connect(self._on_report)
        engine.started.connect(self._on_engine_started)
        engine.stopping.connect(self._on_engine_stopping)
        self._dur_unit_idx = 0  # 持续时间单位索引（秒/分/时/天）
        self._waiting_start = False
        self._startup_busy = False   # 是否正在显示启动等待遮罩
        self._startup_configs = None # 延迟启动时暂存配置
        self._num_targets = 1
        self._restore_form()

    def _restore_form(self):
        """启动时恢复上次填写的目标配置（本地持久化）。"""
        f = settings.stress_form or {}
        try:
            if f.get("target"):
                self.targetEdit.setPlainText(str(f["target"]))
            if f.get("port"):
                self.portSpin.setValue(int(f["port"]))
            if f.get("protocol"):
                idx = self.protoCombo.findText(str(f["protocol"]))
                if idx >= 0:
                    self.protoCombo.setCurrentIndex(idx)
                # 协议切换会自动改端口，恢复用户实际用的端口
                if f.get("port"):
                    self.portSpin.setValue(int(f["port"]))
            if f.get("threads"):
                self.threadSpin.setValue(int(f["threads"]))
            if f.get("rate"):
                self.rateSpin.setValue(int(f["rate"]))
            if f.get("dur"):
                self._dur_unit_idx = int(f.get("dur_unit", 0))
                self.durUnitCombo.setCurrentIndex(self._dur_unit_idx)
                self.durSpin.setRange(1, self.DUR_MAX[self._dur_unit_idx])
                self.durSpin.setValue(int(f["dur"]))
            if f.get("headers"):
                self.headersEdit.setPlainText(str(f["headers"]))
        except Exception:
            pass

    def _save_form(self):
        """把当前表单状态存到本地，下次启动恢复。"""
        settings.set("stress_form", {
            "target": self.targetEdit.toPlainText().strip(),
            "port": self.portSpin.value(),
            "protocol": self.protoCombo.currentText(),
            "threads": self.threadSpin.value(),
            "rate": self.rateSpin.value(),
            "dur": self.durSpin.value(),
            "dur_unit": max(0, self.durUnitCombo.currentIndex()),
            "headers": self.headersEdit.toPlainText().strip(),
        })

    # 持续时间单位：索引 → 字符串标识（导入导出用，比索引更稳定）
    _DUR_UNIT_NAMES = ("sec", "min", "hour", "day")

    def _collect_config(self) -> dict:
        """从当前表单收集配置数据为 dict（用于导出）。"""
        targets = [ln.strip() for ln in self.targetEdit.toPlainText().splitlines() if ln.strip()]
        dur_idx = max(0, self.durUnitCombo.currentIndex())
        headers_raw = self.headersEdit.toPlainText().strip()
        try:
            headers = json.loads(headers_raw) if headers_raw else {}
        except (json.JSONDecodeError, ValueError):
            headers = {}  # 导出时遇到非法 JSON 就置空，不报错
        return {
            "version": CONFIG_VERSION,
            "targets": targets,
            "port": self.portSpin.value(),
            "protocol": self.protoCombo.currentText(),
            "threads": self.threadSpin.value(),
            "rate": self.rateSpin.value(),
            "duration_value": self.durSpin.value(),
            "duration_unit": self._DUR_UNIT_NAMES[dur_idx],
            "headers": headers,
        }

    def _apply_config(self, cfg: dict) -> bool:
        """将配置 dict 填充到表单。返回 True 表示成功。"""
        try:
            # 校验必填字段
            if not isinstance(cfg.get("targets"), list) or not cfg["targets"]:
                InfoBar.warning(L("配置无效", "Invalid Config"),
                                L("配置文件缺少目标地址", "Config file is missing targets"),
                                parent=self.window())
                return False
            # 协议白名单
            proto = str(cfg.get("protocol", "HTTP")).upper()
            valid_protos = {"HTTP", "HTTPS", "TCP", "UDP", "ICMP"}
            if proto not in valid_protos:
                proto = "HTTP"
            # 持续时间单位
            dur_unit_name = str(cfg.get("duration_unit", "sec"))
            dur_idx = self._DUR_UNIT_NAMES.index(dur_unit_name) if dur_unit_name in self._DUR_UNIT_NAMES else 0
            dur_val = int(cfg.get("duration_value", 30))
            dur_val = max(1, min(dur_val, self.DUR_MAX[dur_idx]))
            # 填充表单
            self.targetEdit.setPlainText("\n".join(str(t) for t in cfg["targets"]))
            idx = self.protoCombo.findText(proto)
            if idx >= 0:
                self.protoCombo.setCurrentIndex(idx)
            self.portSpin.setValue(int(cfg.get("port", 80)))
            self.threadSpin.setValue(int(cfg.get("threads", settings.default_threads)))
            self.rateSpin.setValue(int(cfg.get("rate", settings.default_rate)))
            self._dur_unit_idx = dur_idx
            self.durUnitCombo.setCurrentIndex(dur_idx)
            self.durSpin.setRange(1, self.DUR_MAX[dur_idx])
            self.durSpin.setValue(dur_val)
            # 请求头
            headers = cfg.get("headers", {})
            if isinstance(headers, dict) and headers:
                self.headersEdit.setPlainText(json.dumps(headers, ensure_ascii=False, indent=2))
            else:
                self.headersEdit.setPlainText("")
            self._save_form()  # 同步持久化
            return True
        except Exception as e:
            InfoBar.error(L("导入失败", "Import Failed"),
                          L(f"配置文件格式错误：{e}", f"Bad config format: {e}"),
                          parent=self.window())
            return False

    def _export_config(self):
        """导出当前配置为 JSON 文件。"""
        targets = [ln.strip() for ln in self.targetEdit.toPlainText().splitlines() if ln.strip()]
        if not targets:
            InfoBar.warning(L("无法导出", "Cannot Export"),
                            L("请至少填写一个目标地址", "Enter at least one target before exporting"),
                            parent=self.window())
            return
        # 生成默认文件名（第一个目标 + 时间戳），清理 Windows 文件名非法字符
        first = targets[0]
        for ch in ('\\', '/', ':', '*', '?', '"', '<', '>', '|', '#', '&', '%'):
            first = first.replace(ch, '_')
        first = first.replace("https___", "").replace("http___", "").strip("_")
        first = first[:40]  # 防止文件名过长
        ts = _time.strftime("%Y%m%d_%H%M%S")
        default_name = f"netpulse_{first}_{ts}.json"
        path, _ = QFileDialog.getSaveFileName(
            self.window(),
            L("导出配置", "Export Config"),
            default_name,
            "JSON (*.json)",
        )
        if not path:
            return
        cfg = self._collect_config()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, ensure_ascii=False, indent=2)
            InfoBar.success(L("导出成功", "Exported"),
                            L(f"已保存到 {path}", f"Saved to {path}"),
                            parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            log.info(f"配置已导出: {path}")
        except OSError as e:
            InfoBar.error(L("导出失败", "Export Failed"),
                          L(f"无法写入文件：{e}", f"Cannot write file: {e}"),
                          parent=self.window())

    def _import_config(self):
        """从 JSON 文件导入配置并填充表单。"""
        if engine.running:
            InfoBar.warning(L("无法导入", "Cannot Import"),
                            L("测试正在运行中，请先停止", "Test is running; stop it first"),
                            parent=self.window())
            return
        path, _ = QFileDialog.getOpenFileName(
            self.window(),
            L("导入配置", "Import Config"),
            "",
            "JSON (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            InfoBar.error(L("导入失败", "Import Failed"),
                          L(f"无法读取文件：{e}", f"Cannot read file: {e}"),
                          parent=self.window())
            return
        if not isinstance(cfg, dict):
            InfoBar.error(L("导入失败", "Import Failed"),
                          L("配置文件格式无效", "Config file has invalid format"),
                          parent=self.window())
            return
        # 版本兼容检查（将来有新版本可做迁移）
        ver = cfg.get("version", 0)
        if ver > CONFIG_VERSION:
            InfoBar.warning(L("版本提示", "Version Notice"),
                            L(f"配置文件来自更新版本的 NetPulse（v{ver}），部分设置可能无法识别。",
                              f"Config is from a newer NetPulse (v{ver}); some settings may be ignored."),
                            parent=self.window(), duration=4000)
        if self._apply_config(cfg):
            n = len(cfg.get("targets", []))
            InfoBar.success(L("导入成功", "Imported"),
                            L(f"已加载 {n} 个目标配置", f"Loaded {n} target(s)"),
                            parent=self.window(), position=InfoBarPosition.TOP, duration=3000)
            log.info(f"配置已导入: {path}")

    # ---------- 构建界面 ----------

    def _build_config_card(self):
        card = SimpleCardWidget(self.view)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)
        lay.addWidget(StrongBodyLabel(L("目标配置", "Target Configuration"), card))

        lay.addWidget(BodyLabel(L("目标地址（每行一个，支持多目标同时测试）",
                                  "Targets (one per line; multiple targets run in parallel)"), card))
        self.targetEdit = TextEdit(card)
        self.targetEdit.setPlaceholderText(L("https://example.com\n127.0.0.1\napi.example.com",
                                             "https://example.com\n127.0.0.1\napi.example.com"))
        self.targetEdit.setFixedHeight(92)
        self.targetEdit.setAcceptRichText(False)
        lay.addWidget(self.targetEdit)

        prow = QHBoxLayout()
        self.portSpin = SpinBox(card)
        self.portSpin.setRange(1, 65535)
        self.portSpin.setValue(80)
        self.protoCombo = ComboBox(card)
        self.protoCombo.addItems(["HTTP", "HTTPS", "TCP", "UDP", "ICMP"])
        self.protoCombo.currentTextChanged.connect(
            lambda t: self.portSpin.setValue(443 if t == "HTTPS" else 80))
        prow.addWidget(self._wrap(BodyLabel(L("端口", "Port"), card), self.portSpin))
        prow.addWidget(self._wrap(BodyLabel(L("协议", "Protocol"), card), self.protoCombo))
        lay.addLayout(prow)

        lay.addWidget(BodyLabel(L("并发线程数（每目标）", "Concurrency Threads (per target)"), card))
        thread_row = QHBoxLayout()
        self.threadSlider = Slider(Qt.Horizontal, card)
        self.threadSlider.setRange(1, 1024)
        self.threadSpin = SpinBox(card)
        self.threadSpin.setRange(1, 1024)
        self.threadSlider.setValue(settings.default_threads)
        self.threadSpin.setValue(settings.default_threads)
        self.threadSlider.valueChanged.connect(self.threadSpin.setValue)
        self.threadSpin.valueChanged.connect(self.threadSlider.setValue)
        thread_row.addWidget(self.threadSlider, 1)
        thread_row.addWidget(self.threadSpin)
        lay.addLayout(thread_row)

        row2 = QHBoxLayout()
        # 持续时间：数值 + 单位（秒/分/时/天）
        dur_wrap = QWidget(card)
        dv = QVBoxLayout(dur_wrap)
        dv.setContentsMargins(0, 0, 0, 0)
        dv.setSpacing(4)
        dv.addWidget(BodyLabel(L("持续时间", "Duration"), dur_wrap))
        dur_row = QHBoxLayout()
        dur_row.setContentsMargins(0, 0, 0, 0)
        dur_row.setSpacing(6)
        self.durSpin = SpinBox(dur_wrap)
        self.durSpin.setRange(1, 3600)
        self.durSpin.setValue(settings.default_duration)
        self.durUnitCombo = ComboBox(dur_wrap)
        self.durUnitCombo.addItems([L("秒", "sec"), L("分钟", "min"), L("小时", "hour"), L("天", "day")])
        self.durUnitCombo.currentIndexChanged.connect(self._on_dur_unit_changed)
        dur_row.addWidget(self.durSpin, 1)
        dur_row.addWidget(self.durUnitCombo)
        dv.addLayout(dur_row)
        self.rateSpin = SpinBox(card)
        self.rateSpin.setRange(1, 100000)
        self.rateSpin.setValue(settings.default_rate)
        row2.addWidget(dur_wrap)
        row2.addWidget(self._wrap(BodyLabel(L("速率上限(QPS)", "Rate Limit (QPS)"), card), self.rateSpin))
        lay.addLayout(row2)

        lay.addWidget(BodyLabel(L("请求头(HTTP, 可选)", "Headers (HTTP, optional)"), card))
        self.headersEdit = TextEdit(card)
        self.headersEdit.setPlaceholderText('{"Authorization": "Bearer ..."}')
        self.headersEdit.setFixedHeight(56)
        lay.addWidget(self.headersEdit)

        # 授权列表
        lay.addSpacing(6)
        lay.addWidget(StrongBodyLabel(L("已授权目标", "Authorized Targets"), card))
        self.authListLabel = BodyLabel("", card)
        self.authListLabel.setWordWrap(True)
        lay.addWidget(self.authListLabel)
        self.refresh_auth_list()

        # 导入/导出配置按钮
        lay.addSpacing(6)
        io_row = QHBoxLayout()
        self.exportBtn = PushButton(L("导出配置", "Export Config"), card)
        self.exportBtn.clicked.connect(self._export_config)
        self.importBtn = PushButton(L("导入配置", "Import Config"), card)
        self.importBtn.clicked.connect(self._import_config)
        io_row.addWidget(self.importBtn)
        io_row.addWidget(self.exportBtn)
        io_row.addStretch(1)
        lay.addLayout(io_row)
        return card

    def _wrap(self, label, widget):
        w = QWidget(self.view)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(4)
        v.addWidget(label)
        v.addWidget(widget)
        return w

    def _build_stats_card(self):
        card = SimpleCardWidget(self.view)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)

        status_row = QHBoxLayout()
        status_row.addWidget(StrongBodyLabel(L("运行状态", "Status"), card))
        status_row.addStretch(1)
        self.statusLabel = BodyLabel(L("就绪", "Ready"), card)
        status_row.addWidget(self.statusLabel)
        lay.addLayout(status_row)

        self.progressBar = ProgressBar(card)
        self.progressBar.setValue(0)
        lay.addWidget(self.progressBar)

        grid = QGridLayout()
        grid.setSpacing(10)
        self.mTotal = MiniStat("#0078D4", card)
        self.mSuccess = MiniStat("#107C10", card)
        self.mFail = MiniStat("#D13438", card)
        self.mQps = MiniStat("#0078D4", card)
        self.mAvg = MiniStat("#8764B8", card)
        self.mTx = MiniStat("#00B7C3", card)
        self.mActive = MiniStat(_subtle_text_color(), card)
        grid.addWidget(self._mini(L("已发送", "Sent"), self.mTotal), 0, 0)
        grid.addWidget(self._mini(L("成功", "Success"), self.mSuccess), 0, 1)
        grid.addWidget(self._mini(L("失败", "Failed"), self.mFail), 0, 2)
        grid.addWidget(self._mini(L("实时 QPS", "Live QPS"), self.mQps), 1, 0)
        grid.addWidget(self._mini(L("平均延迟(ms)", "Avg Latency (ms)"), self.mAvg), 1, 1)
        grid.addWidget(self._mini(L("活跃线程", "Active Threads"), self.mActive), 1, 2)
        grid.addWidget(self._mini(L("总发送流量", "Total Sent Traffic"), self.mTx), 2, 0)
        lay.addLayout(grid)

        # 最近失败原因（实时）
        self.errLabel = CaptionLabel(L("最近失败原因：—", "Last error: —"), card)
        self.errLabel.setStyleSheet("color:#D13438; background:transparent;")
        self.errLabel.setWordWrap(True)
        lay.addWidget(self.errLabel)

        # 分目标实时状态（多目标时显示每个目标的成功/失败）
        self.targetsLabel = CaptionLabel("", card)
        self.targetsLabel.setStyleSheet("color:#0078D4; background:transparent;")
        self.targetsLabel.setWordWrap(True)
        lay.addWidget(self.targetsLabel)

        lay.addSpacing(4)
        btn_row = QHBoxLayout()
        self.startBtn = PrimaryPushButton(L("开始测试", "Start"), card)
        self.stopBtn = PushButton(L("停止测试", "Stop"), card)
        self.stopBtn.setEnabled(False)
        self.startBtn.clicked.connect(self._start)
        self.stopBtn.clicked.connect(self._stop)
        btn_row.addWidget(self.startBtn)
        btn_row.addWidget(self.stopBtn)
        btn_row.addStretch(1)
        lay.addLayout(btn_row)

        tip = CaptionLabel(L("提示：所有目标须先通过授权确认；速率与并发受令牌桶限速保护。",
                             "Note: every target requires authorization; rate is capped by token bucket."), card)
        lay.addWidget(tip)
        return card

    def _mini(self, title, value_label):
        w = QWidget(self.view)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(CaptionLabel(title, w))
        v.addWidget(value_label)
        return w

    # ---------- 逻辑 ----------

    # 单位换算表：索引对应下拉框选项（秒/分/时/天）
    DUR_FACTORS = (1, 60, 3600, 86400)
    DUR_MAX = (3600, 24 * 60, 72, 30)   # 每个单位下的数值上限

    def _on_dur_unit_changed(self, idx):
        """切换单位时保持总时长不变（尽量整除），并调整数值范围。"""
        old_idx = getattr(self, "_dur_unit_idx", 0)
        if old_idx == idx:
            return
        old_v = self.durSpin.value()
        total_sec = old_v * self.DUR_FACTORS[old_idx]
        new_factor = self.DUR_FACTORS[idx]
        self.durSpin.setRange(1, self.DUR_MAX[idx])
        self.durSpin.setValue(max(1, round(total_sec / new_factor)))
        self._dur_unit_idx = idx

    def get_duration_seconds(self) -> int:
        """按当前单位换算成秒。"""
        idx = self.durUnitCombo.currentIndex()
        idx = 0 if idx < 0 else idx
        return self.durSpin.value() * self.DUR_FACTORS[idx]

    def refresh_auth_list(self):
        hosts = [a["host"] for a in settings.authorized]
        self.authListLabel.setText(", ".join(hosts) if hosts else L("（暂无）", "(none)"))

    def _parse_targets(self):
        """解析多行目标输入 → [(原始行, 规范化host)]，去重保序；空返回 []。"""
        targets, seen = [], set()
        for ln in self.targetEdit.toPlainText().splitlines():
            ln = ln.strip()
            if not ln:
                continue
            host = normalize_host(ln)
            if not host:
                InfoBar.warning(L("参数错误", "Invalid input"),
                                L(f"无效目标：{ln}", f"Invalid target: {ln}"), parent=self.window())
                return None
            if host in seen:
                continue
            seen.add(host)
            targets.append((ln, host))
        return targets

    def _start(self):
        targets = self._parse_targets()
        if targets is None:
            return
        if not targets:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请至少输入一个目标地址", "Enter at least one target"), parent=self.window())
            return
        proto = self.protoCombo.currentText()

        # 逐个目标授权确认
        for _, host in targets:
            if not is_authorized(host):
                dlg = AuthDialog(host, self.window())
                if not dlg.exec():
                    InfoBar.warning(L("已取消", "Cancelled"),
                                    L(f"目标 {host} 未授权，测试已阻止", f"Target {host} not authorized; test blocked"),
                                    parent=self.window())
                    return
                add_authorized(host, dlg.note())
        self.refresh_auth_list()

        rate = self.rateSpin.value()
        if rate > HIGH_RATE:
            n = len(targets)
            w = MessageBox(L("高请求速率二次确认", "High Rate Confirmation"),
                           L(f"每个目标速率上限 {rate} QPS，共 {n} 个目标（合计约 {rate * n} QPS）。"
                             f"请再次确认您拥有全部目标授权，且目标可承受该速率。",
                             f"Rate cap is {rate} QPS per target, {n} target(s) total (~{rate * n} QPS combined). "
                             f"Confirm again that all targets are authorized and can handle this rate."),
                           self.window())
            if not w.exec():
                InfoBar.warning(L("已取消", "Cancelled"),
                                L("高速率未确认，测试已取消", "High rate not confirmed; cancelled"),
                                parent=self.window())
                return

        port = self.portSpin.value()
        try:
            headers = json.loads(self.headersEdit.toPlainText()) if self.headersEdit.toPlainText().strip() else {}
        except json.JSONDecodeError:
            InfoBar.warning(L("请求头格式错误", "Invalid headers"),
                            L("请求头须为合法 JSON", "Headers must be valid JSON"), parent=self.window())
            return

        configs = []
        for raw, host in targets:
            url = ""
            if proto in ("HTTP", "HTTPS"):
                url = raw if raw.startswith("http") else f"{proto.lower()}://{host}"
                default_port = 443 if proto == "HTTPS" else 80
                if port != default_port:
                    url += f":{port}"
            configs.append({
                "target": host, "port": port, "protocol": proto, "url": url,
                "threads": self.threadSpin.value(), "duration": self.get_duration_seconds(),
                "rate": rate, "packet_size": settings.default_packet_size,
                "timeout": settings.default_timeout_ms, "headers": headers,
            })

        self._save_form()  # 持久化本次配置，重启后自动恢复
        hosts = ", ".join(c["target"] for c in configs)
        log.info(f"开始压测({len(configs)}目标): {hosts} threads={configs[0]['threads']} "
                 f"rate={rate} duration={configs[0]['duration']}s")

        # 立即切换UI状态，给用户即时反馈
        self.startBtn.setEnabled(False)
        self.stopBtn.setEnabled(True)
        n = len(configs)
        self._num_targets = n
        self.statusLabel.setText(L("启动中...", "Starting..."))
        self.progressBar.setValue(0)
        self.mTotal.setText("0")
        self.mSuccess.setText("0")
        self.mFail.setText("0")
        self.mQps.setText("0.0")
        self.mAvg.setText("0.0")
        self.mActive.setText("0")
        self.mTx.setText("0 B")
        self.errLabel.setText(L("最近失败原因：—", "Last error: —"))
        self.targetsLabel.setText("")

        # 立即显示等待遮罩，给用户明确的"正在启动"反馈
        total_threads = configs[0]["threads"] * n
        win = self.window()
        if hasattr(win, "show_busy"):
            self._startup_busy = True
            win.show_busy(L("正在启动压测...", "Starting stress test..."),
                          L(f"正在创建 {total_threads} 个 worker 线程", f"Creating {total_threads} worker threads"))

        # 延迟80ms再真正启动引擎，确保遮罩先完成渲染，避免UI无响应的感觉
        self._startup_configs = configs
        QTimer.singleShot(80, self._do_start_engine)

    def _do_start_engine(self):
        """延迟执行引擎启动，确保等待遮罩已渲染。"""
        configs = self._startup_configs
        self._startup_configs = None
        ok = engine.start(configs)
        if not ok:
            self._hide_startup_busy()
            self.startBtn.setEnabled(True)
            self.stopBtn.setEnabled(False)
            self.statusLabel.setText(L("就绪", "Ready"))
            InfoBar.warning(L("启动失败", "Start failed"),
                            L("无法启动压测，请检查配置", "Cannot start stress test, check configuration"),
                            parent=self.window())
            return
        # 安全超时：5秒后强制隐藏遮罩（防止异常情况下遮罩永远不消失）
        QTimer.singleShot(5000, self._hide_startup_busy)

    def _hide_startup_busy(self):
        """隐藏启动等待遮罩（确保只隐藏一次）。"""
        if self._startup_busy:
            self._startup_busy = False
            win = self.window()
            if hasattr(win, "hide_busy"):
                win.hide_busy()

    def _stop(self):
        # 如果还在启动阶段就点击停止，先清除启动遮罩标记（停止遮罩会覆盖它）
        self._startup_busy = False
        win = self.window()
        if hasattr(win, "show_busy"):
            win.show_busy(L("正在停止...", "Stopping..."),
                          L("等待 worker 线程退出", "Waiting for worker threads to exit"))
        engine.stop()
        log.info("手动停止压测")

    def _on_engine_started(self):
        """所有 worker 线程已创建完成，更新状态文字。遮罩等真正开始跑数据时再隐藏。"""
        n = self._num_targets
        self.statusLabel.setText(L("运行中", "Running") if n == 1
                                 else L(f"运行中 · {n} 个目标", f"Running · {n} targets"))

    def _on_engine_stopping(self):
        """引擎正在停止（等待所有 worker 退出）。"""
        pass

    def _on_snapshot(self, d):
        # 更新实时统计数据
        self.mTotal.setText(str(d["total"]))
        self.mSuccess.setText(str(d["success"]))
        self.mFail.setText(str(d["fail"]))
        self.mTx.setText(fmt_bytes(d.get("tx", 0)))
        self.mQps.setText(f"{d['qps']:.1f}")
        self.mAvg.setText(f"{d['avg']:.1f}")
        active = d.get("active", 0)
        self.mActive.setText(str(active))
        self.progressBar.setValue(int(d["progress"] * 100))
        last_err = d.get("last_error") or ""
        if last_err:
            self.errLabel.setText(L(f"最近失败原因：{err_text(last_err)}",
                                    f"Last error: {err_text(last_err)}"))
        else:
            self.errLabel.setText(L("最近失败原因：—", "Last error: —"))
        # 分目标实时状态
        parts = [f"{t['host']}: ✓{t['success']} ✗{t['fail']} ({t['qps']:.0f} QPS)"
                 for t in d.get("targets", [])]
        self.targetsLabel.setText("  |  ".join(parts))

        # worker线程真正跑起来了（有活跃线程），隐藏启动遮罩
        if self._startup_busy and active > 0:
            self._hide_startup_busy()

    def _on_report(self, r):
        # 压测结束，隐藏等待遮罩
        self._waiting_start = False
        self._startup_busy = False
        win = self.window()
        if hasattr(win, "hide_busy"):
            win.hide_busy()

        self.startBtn.setEnabled(True)
        self.stopBtn.setEnabled(False)
        self.statusLabel.setText(L("已完成", "Completed"))
        self.progressBar.setValue(100)
        err_rate = (r["fail"] / r["total"] * 100) if r["total"] else 0.0
        dur = r["duration"]
        dur_text = (f"{dur:.1f} " + L("秒", "s")) if dur < 60 else (f"{dur / 60:.1f} " + L("分钟", "min"))
        targets = r.get("targets") or []

        # 多目标：逐目标明细 + 汇总
        if len(targets) > 1:
            text = L(f"共 {len(targets)} 个目标  |  持续 {dur_text}\n",
                     f"{len(targets)} targets  |  Duration {dur_text}\n")
            for t in targets:
                ter = (t["fail"] / t["total"] * 100) if t["total"] else 0.0
                text += L(f"• {t['protocol']}://{t['target']}  共 {t['total']} 成功 {t['success']} "
                          f"失败 {t['fail']}（{ter:.1f}%）平均 {t['avg']:.1f} ms  {fmt_bytes(t.get('bytes_tx', 0))}\n",
                          f"• {t['protocol']}://{t['target']}  total {t['total']} ok {t['success']} "
                          f"fail {t['fail']} ({ter:.1f}%) avg {t['avg']:.1f} ms  {fmt_bytes(t.get('bytes_tx', 0))}\n")
            text += L(f"合计 {r['total']}  成功 {r['success']}  失败 {r['fail']}（错误率 {err_rate:.2f}%）\n",
                      f"Total {r['total']}  success {r['success']}  failed {r['fail']} (error rate {err_rate:.2f}%)\n")
        else:
            text = (
                L(f"目标 {r['protocol']}://{r['target']}  |  持续 {dur_text}\n",
                  f"Target {r['protocol']}://{r['target']}  |  Duration {dur_text}\n")
                + L(f"总请求 {r['total']}  成功 {r['success']}  失败 {r['fail']}（错误率 {err_rate:.2f}%）\n",
                    f"Total {r['total']}  Success {r['success']}  Failed {r['fail']} (error rate {err_rate:.2f}%)\n")
            )
        text += (
            L(f"平均延迟 {r['avg']:.1f} ms   P50 {r['p50']:.1f} ms   P90 {r['p90']:.1f} ms   P99 {r['p99']:.1f} ms\n",
              f"Avg latency {r['avg']:.1f} ms   P50 {r['p50']:.1f} ms   P90 {r['p90']:.1f} ms   P99 {r['p99']:.1f} ms\n")
            + L(f"总发送流量 {fmt_bytes(r.get('bytes_tx', 0))}   速率上限 {r['rate_limit']} QPS",
                f"Total sent {fmt_bytes(r.get('bytes_tx', 0))}   Rate cap {r['rate_limit']} QPS")
        )
        errors = r.get("errors") or {}
        if errors:
            top = sorted(errors.items(), key=lambda kv: -kv[1])[:5]
            sep = L("，", ", ")
            times = L("×", "x")
            breakdown = sep.join(f"{err_text(k)} {times}{v}" for k, v in top)
            text += "\n" + L(f"失败原因分布：{breakdown}", f"Failure reasons: {breakdown}")
        self.reportLabel.setText(text)
        log.info(f"压测完成: total={r['total']} success={r['success']} fail={r['fail']} errors={errors}")

    def fill_defaults(self, target="", port=80, protocol="HTTP"):
        """快速开始入口。"""
        if target:
            self.targetEdit.setPlainText(target)
        self.portSpin.setValue(port)
        idx = self.protoCombo.findText(protocol)
        if idx >= 0:
            self.protoCombo.setCurrentIndex(idx)

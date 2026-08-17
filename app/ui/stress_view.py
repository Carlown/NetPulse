"""压力测试页：左侧配置 + 右侧实时统计与报告。"""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QGridLayout, QHBoxLayout, QLabel,
                               QVBoxLayout, QWidget)
from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, InfoBar,
                            InfoBarPosition, LineEdit, MessageBox,
                            PrimaryPushButton, ProgressBar, PushButton,
                            ScrollArea, SimpleCardWidget, Slider, SpinBox,
                            StrongBodyLabel, SubtitleLabel, TextEdit)

from app.services.auth import add_authorized, is_authorized, normalize_host, remove_authorized
from app.services.logger import log
from app.services.settings import settings
from app.services.stress import engine
from app.ui.disclaimer import AuthDialog
from app.ui.i18n import L

HIGH_RATE = 500  # 高速率二次确认阈值

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
        self._restore_form()

    def _restore_form(self):
        """启动时恢复上次填写的目标配置（本地持久化）。"""
        f = settings.stress_form or {}
        try:
            if f.get("target"):
                self.targetEdit.setText(str(f["target"]))
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
        except Exception:
            pass

    def _save_form(self):
        """把当前表单状态存到本地，下次启动恢复。"""
        settings.set("stress_form", {
            "target": self.targetEdit.text().strip(),
            "port": self.portSpin.value(),
            "protocol": self.protoCombo.currentText(),
            "threads": self.threadSpin.value(),
            "rate": self.rateSpin.value(),
            "dur": self.durSpin.value(),
            "dur_unit": max(0, self.durUnitCombo.currentIndex()),
        })

    # ---------- 构建界面 ----------

    def _build_config_card(self):
        card = SimpleCardWidget(self.view)
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(10)
        lay.addWidget(StrongBodyLabel(L("目标配置", "Target Configuration"), card))

        self.targetEdit = LineEdit(card)
        self.targetEdit.setPlaceholderText(L("目标地址（如 127.0.0.1 或 https://example.com）",
                                             "Target (e.g. 127.0.0.1 or https://example.com)"))
        lay.addWidget(BodyLabel(L("目标地址", "Target"), card))
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

        lay.addWidget(BodyLabel(L("并发线程数", "Concurrency Threads"), card))
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
        self.mActive = MiniStat("#6B6B6B", card)
        self.mTx = MiniStat("#00B7C3", card)
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

    def _start(self):
        target_raw = self.targetEdit.text().strip()
        host = normalize_host(target_raw)
        if not host:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请输入目标地址", "Please enter a target"), parent=self.window())
            return
        proto = self.protoCombo.currentText()
        if not is_authorized(host):
            dlg = AuthDialog(host, self.window())
            if not dlg.exec():
                InfoBar.warning(L("已取消", "Cancelled"),
                                L("目标未授权，测试已阻止", "Target not authorized; test blocked"),
                                parent=self.window())
                return
            add_authorized(host, dlg.note())
            self.refresh_auth_list()

        rate = self.rateSpin.value()
        if rate > HIGH_RATE:
            w = MessageBox(L("高请求速率二次确认", "High Rate Confirmation"),
                           L(f"速率上限将设置为 {rate} QPS。请再次确认您拥有 {host} 的授权，且目标可承受该速率。",
                             f"Rate limit will be {rate} QPS. Confirm again that {host} is authorized "
                             f"and can handle this rate."), self.window())
            if not w.exec():
                InfoBar.warning(L("已取消", "Cancelled"),
                                L("高速率未确认，测试已取消", "High rate not confirmed; cancelled"),
                                parent=self.window())
                return

        port = self.portSpin.value()
        if proto in ("HTTP", "HTTPS"):
            url = target_raw if target_raw.startswith("http") else f"{proto.lower()}://{host}"
            if proto == "HTTP" and port != 80:
                url += f":{port}"
            elif proto == "HTTPS" and port != 443:
                url += f":{port}"
        else:
            url = ""
        try:
            headers = json_loads(self.headersEdit.toPlainText()) if self.headersEdit.toPlainText().strip() else {}
        except ValueError:
            InfoBar.warning(L("请求头格式错误", "Invalid headers"),
                            L("请求头须为合法 JSON", "Headers must be valid JSON"), parent=self.window())
            return

        config = {
            "target": host, "port": port, "protocol": proto, "url": url,
            "threads": self.threadSpin.value(), "duration": self.get_duration_seconds(),
            "rate": rate, "packet_size": settings.default_packet_size,
            "timeout": settings.default_timeout_ms, "headers": headers,
        }
        self._save_form()  # 持久化本次配置，重启后自动恢复
        log.info(f"开始压测: {proto}://{host}:{port} threads={config['threads']} rate={rate} duration={config['duration']}s")
        engine.start(config)
        self.startBtn.setEnabled(False)
        self.stopBtn.setEnabled(True)
        self.statusLabel.setText(L("运行中", "Running"))
        self.progressBar.setValue(0)
        self.mTx.setText("0 B")
        self.errLabel.setText(L("最近失败原因：—", "Last error: —"))

    def _stop(self):
        engine.stop()
        log.info("手动停止压测")

    def _on_snapshot(self, d):
        self.mTotal.setText(str(d["total"]))
        self.mSuccess.setText(str(d["success"]))
        self.mFail.setText(str(d["fail"]))
        self.mTx.setText(fmt_bytes(d.get("tx", 0)))
        self.mQps.setText(f"{d['qps']:.1f}")
        self.mAvg.setText(f"{d['avg']:.1f}")
        self.mActive.setText(str(d["active"]))
        self.progressBar.setValue(int(d["progress"] * 100))
        last_err = d.get("last_error") or ""
        if last_err:
            self.errLabel.setText(L(f"最近失败原因：{err_text(last_err)}",
                                    f"Last error: {err_text(last_err)}"))
        else:
            self.errLabel.setText(L("最近失败原因：—", "Last error: —"))

    def _on_report(self, r):
        self.startBtn.setEnabled(True)
        self.stopBtn.setEnabled(False)
        self.statusLabel.setText(L("已完成", "Completed"))
        self.progressBar.setValue(100)
        err_rate = (r["fail"] / r["total"] * 100) if r["total"] else 0.0
        dur = r["duration"]
        dur_text = (f"{dur:.1f} " + L("秒", "s")) if dur < 60 else (f"{dur / 60:.1f} " + L("分钟", "min"))
        text = (
            L(f"目标 {r['protocol']}://{r['target']}  |  持续 {dur_text}\n",
              f"Target {r['protocol']}://{r['target']}  |  Duration {dur_text}\n")
            + L(f"总请求 {r['total']}  成功 {r['success']}  失败 {r['fail']}（错误率 {err_rate:.2f}%）\n",
                f"Total {r['total']}  Success {r['success']}  Failed {r['fail']} (error rate {err_rate:.2f}%)\n")
            + L(f"平均延迟 {r['avg']:.1f} ms   P50 {r['p50']:.1f} ms   P90 {r['p90']:.1f} ms   P99 {r['p99']:.1f} ms\n",
                f"Avg latency {r['avg']:.1f} ms   P50 {r['p50']:.1f} ms   P90 {r['p90']:.1f} ms   P99 {r['p99']:.1f} ms\n")
            + L(f"总发送流量 {fmt_bytes(r.get('bytes_tx', 0))}   速率上限 {r['rate_limit']} QPS",
                f"Total sent {fmt_bytes(r.get('bytes_tx', 0))}   Rate cap {r['rate_limit']} QPS")
        )
        errors = r.get("errors") or {}
        if errors:
            top = sorted(errors.items(), key=lambda kv: -kv[1])[:5]
            breakdown = "，".join(f"{err_text(k)} ×{v}" for k, v in top)
            text += "\n" + L(f"失败原因分布：{breakdown}", f"Failure reasons: {breakdown}")
        self.reportLabel.setText(text)
        log.info(f"压测完成: total={r['total']} success={r['success']} fail={r['fail']} errors={errors}")

    def fill_defaults(self, target="", port=80, protocol="HTTP"):
        """快速开始入口。"""
        if target:
            self.targetEdit.setText(target)
        self.portSpin.setValue(port)
        idx = self.protoCombo.findText(protocol)
        if idx >= 0:
            self.protoCombo.setCurrentIndex(idx)


def json_loads(s):
    import json
    return json.loads(s)

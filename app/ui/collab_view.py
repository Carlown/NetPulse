"""协同测试页：主控邀请 / 节点加入（直连 + 中继模式）。"""
import time
import threading

from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, InfoBar,
                            InfoBarPosition, LineEdit, PrimaryPushButton,
                            PushButton, ScrollArea, SimpleCardWidget, SpinBox,
                            StrongBodyLabel, SubtitleLabel, SwitchButton)

from app.services.collab import collab_client, collab_server, PORT
from app.services.logger import log
from app.services.stress import engine
from app.ui.i18n import L
from app.ui.stress_view import MiniStat


class CollabView(ScrollArea):
    _net_info_ready = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("collabView")
        self.view = QWidget(self)
        self.setWidget(self.view)
        self.setWidgetResizable(True)
        self.enableTransparentBackground()

        # 节点本地统计快照（用于上报给主控）
        self._local_stats = {"total": 0, "success": 0, "fail": 0, "qps": 0.0}
        self._log_lines = []

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        root.addWidget(SubtitleLabel(L("协同测试", "Collaborative Testing"), self.view))

        # 模式选择：角色 + 连接方式
        mode_row = QHBoxLayout()
        mode_row.addWidget(BodyLabel(L("角色", "Role"), self.view))
        self.roleCombo = ComboBox(self.view)
        self.roleCombo.addItems([L("主控（发起邀请）", "Host (invite)"), L("节点（加入）", "Node (join)")])
        self.roleCombo.currentIndexChanged.connect(self._switch_role)
        mode_row.addWidget(self.roleCombo)
        mode_row.addSpacing(24)

        mode_row.addWidget(BodyLabel(L("连接方式", "Connection"), self.view))
        self.connCombo = ComboBox(self.view)
        self.connCombo.addItems([L("中继（外网推荐）", "Relay (WAN)"), L("直连（局域网）", "Direct (LAN)")])
        self.connCombo.setCurrentIndex(0)  # 默认中继模式
        self.connCombo.currentIndexChanged.connect(self._switch_conn_mode)
        mode_row.addWidget(self.connCombo)
        mode_row.addStretch(1)
        root.addLayout(mode_row)

        cols = QHBoxLayout()
        cols.setSpacing(16)

        # ========== 主控卡片 ==========
        self.hostCard = SimpleCardWidget(self.view)
        hl = QVBoxLayout(self.hostCard)
        hl.setContentsMargins(20, 16, 20, 16)
        hl.setSpacing(10)
        hl.addWidget(StrongBodyLabel(L("发起协同", "Host a Session"), self.hostCard))
        hl.addWidget(BodyLabel(L("最大节点数", "Max Nodes"), self.hostCard))
        self.maxNodesSpin = SpinBox(self.hostCard)
        self.maxNodesSpin.setRange(1, 64)
        self.maxNodesSpin.setValue(8)
        hl.addWidget(self.maxNodesSpin)
        self.genBtn = PrimaryPushButton(L("生成邀请码", "Generate Invite"), self.hostCard)
        self.genBtn.clicked.connect(self._gen_invite)
        hl.addWidget(self.genBtn)

        # 邀请码（点击即可复制）
        self.inviteBtn = PushButton("-", self.hostCard)
        self.inviteBtn.clicked.connect(self._copy_invite)
        self.inviteBtn.setStyleSheet("font-size:22px; font-weight:700; padding:6px 24px;")
        hl.addWidget(self.inviteBtn)

        # 中继模式提示
        self.relayHint = CaptionLabel("", self.hostCard)
        self.relayHint.setWordWrap(True)
        hl.addWidget(self.relayHint)

        # 直连模式：地址信息（仅直连模式显示）
        self.addrLabel = BodyLabel("", self.hostCard)
        self.addrLabel.setWordWrap(True)
        hl.addWidget(self.addrLabel)
        addr_row = QHBoxLayout()
        self.copyPubBtn = PushButton(L("复制公网地址", "Copy Public Address"), self.hostCard)
        self.copyPubBtn.clicked.connect(self._copy_public)
        self.copyLanBtn = PushButton(L("复制局域网地址", "Copy LAN Address"), self.hostCard)
        self.copyLanBtn.clicked.connect(self._copy_lan)
        self.adminBtn = PushButton(L("以管理员重启并放行防火墙", "Restart as admin to open firewall"), self.hostCard)
        self.adminBtn.clicked.connect(self._restart_as_admin)
        self.adminBtn.hide()
        addr_row.addWidget(self.copyPubBtn)
        addr_row.addWidget(self.copyLanBtn)
        addr_row.addWidget(self.adminBtn)
        addr_row.addStretch(1)
        hl.addLayout(addr_row)

        self.pushStartBtn = PushButton(L("广播开始（使用压测页配置）", "Broadcast Start (uses Stress config)"), self.hostCard)
        self.pushStartBtn.clicked.connect(self._push_start)
        self.pushStopBtn = PushButton(L("广播停止", "Broadcast Stop"), self.hostCard)
        self.pushStopBtn.clicked.connect(lambda: (collab_server.broadcast({"type": "stop"}), self._server_log(L("已广播停止", "Stop broadcast"))))
        self.pushStartBtn.setEnabled(False)
        self.pushStopBtn.setEnabled(False)
        hl.addWidget(self.pushStartBtn)
        hl.addWidget(self.pushStopBtn)
        cols.addWidget(self.hostCard, 1)

        # ========== 节点卡片 ==========
        self.nodeCard = SimpleCardWidget(self.view)
        nl = QVBoxLayout(self.nodeCard)
        nl.setContentsMargins(20, 16, 20, 16)
        nl.setSpacing(10)
        nl.addWidget(StrongBodyLabel(L("加入协同", "Join a Session"), self.nodeCard))

        # 中继模式提示
        self.nodeRelayHint = CaptionLabel("", self.nodeCard)
        self.nodeRelayHint.setWordWrap(True)
        nl.addWidget(self.nodeRelayHint)

        # 直连模式地址输入
        self.hostLabel = BodyLabel(L("主控地址（内网或公网 IP，可带端口）", "Host address (LAN/WAN IP, port optional)"), self.nodeCard)
        nl.addWidget(self.hostLabel)
        self.hostEdit = LineEdit(self.nodeCard)
        self.hostEdit.setPlaceholderText(L("192.168.1.100:50505 或 1.2.3.4:50505",
                                            "192.168.1.100:50505 or 1.2.3.4:50505"))
        nl.addWidget(self.hostEdit)

        nl.addWidget(BodyLabel(L("邀请码", "Invite Code"), self.nodeCard))
        self.codeEdit = LineEdit(self.nodeCard)
        self.codeEdit.setPlaceholderText("ABC123")
        nl.addWidget(self.codeEdit)
        nl.addWidget(BodyLabel(L("节点名称", "Node Name"), self.nodeCard))
        self.nameEdit = LineEdit(self.nodeCard)
        import socket as _s
        try:
            self.nameEdit.setText(_s.gethostname())
        except OSError:
            pass
        nl.addWidget(self.nameEdit)
        self.joinBtn = PrimaryPushButton(L("加入", "Join"), self.nodeCard)
        self.joinBtn.clicked.connect(self._join)
        self.leaveBtn = PushButton(L("退出", "Leave"), self.nodeCard)
        self.leaveBtn.clicked.connect(self._leave)
        self.leaveBtn.setEnabled(False)
        nl.addWidget(self.joinBtn)
        nl.addWidget(self.leaveBtn)
        cols.addWidget(self.nodeCard, 1)

        root.addLayout(cols)

        # 节点统计（主控端聚合显示）
        nodes_card = SimpleCardWidget(self.view)
        ncl = QVBoxLayout(nodes_card)
        ncl.setContentsMargins(20, 16, 20, 14)
        ncl.addWidget(StrongBodyLabel(L("节点状态", "Node Status"), nodes_card))
        self.mTotal = MiniStat("#0078D4", nodes_card)
        self.mSuccess = MiniStat("#107C10", nodes_card)
        self.mQps = MiniStat("#8764B8", nodes_card)
        grid = QGridLayout()
        grid.addWidget(self._mini(L("累计请求", "Total Requests"), self.mTotal), 0, 0)
        grid.addWidget(self._mini(L("累计成功", "Total Success"), self.mSuccess), 0, 1)
        grid.addWidget(self._mini(L("实时 QPS", "Live QPS"), self.mQps), 0, 2)
        ncl.addLayout(grid)
        self.nodeListLabel = CaptionLabel(L("（暂无节点连接）", "(no nodes connected)"), nodes_card)
        self.nodeListLabel.setWordWrap(True)
        ncl.addWidget(self.nodeListLabel)
        root.addWidget(nodes_card)

        # 日志
        log_card = SimpleCardWidget(self.view)
        lcl = QVBoxLayout(log_card)
        lcl.setContentsMargins(20, 16, 20, 14)
        lcl.addWidget(StrongBodyLabel(L("协同日志", "Collab Log"), log_card))
        self.logLabel = CaptionLabel(L("（暂无）", "(empty)"), log_card)
        self.logLabel.setWordWrap(True)
        lcl.addWidget(self.logLabel)
        root.addWidget(log_card)
        root.addStretch(1)

        # 信号
        self._net_info_ready.connect(self._on_net_info)
        collab_server.log_msg.connect(self._server_log)
        collab_server.nodes_changed.connect(self._update_node_stats)
        collab_client.status_msg.connect(lambda m: self._client_log(m))
        collab_client.start_requested.connect(self._on_remote_start)
        collab_client.stop_requested.connect(lambda: engine.stop())
        engine.snapshot.connect(self._on_local_snapshot)

        # 定时器：主控端定时聚合节点统计；节点端定时上报本地统计
        self._stat_timer = QTimer(self)
        self._stat_timer.timeout.connect(self._tick_stats)
        self._stat_timer.start(1000)

        self._switch_role(0)
        self._switch_conn_mode(0)

    def _mini(self, title, value_label):
        w = QWidget(self.view)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(CaptionLabel(title, w))
        v.addWidget(value_label)
        return w

    def _is_relay_mode(self):
        return self.connCombo.currentIndex() == 0

    def _switch_role(self, idx):
        self.hostCard.setVisible(idx == 0)
        self.nodeCard.setVisible(idx == 1)

    def _switch_conn_mode(self, idx):
        """切换中继/直连模式时更新 UI 显示。"""
        is_relay = (idx == 0)
        relay_desc = "公共 MQTT 中继 (broker.hivemq.com)"

        # 主控侧
        if is_relay:
            self.relayHint.setText(L(
                f"中继模式：通过 {relay_desc} 中转，支持外网节点加入，无需部署服务器、无需公网 IP。",
                f"Relay mode: routed via public MQTT broker, WAN nodes supported, no server setup needed."))
            self.addrLabel.hide()
            self.copyPubBtn.hide()
            self.copyLanBtn.hide()
            self.adminBtn.hide()
        else:
            self.relayHint.setText(L(
                "直连模式：节点需与主控在同一局域网，或主控有公网 IP 并放行防火墙。",
                "Direct mode: nodes must be on the same LAN, or host has a public IP with firewall opened."))
            self.addrLabel.show()
            self.copyPubBtn.show()
            self.copyLanBtn.show()

        # 节点侧
        if is_relay:
            self.nodeRelayHint.setText(L(
                f"中继模式：自动通过 {relay_desc} 连接主控，只需输入邀请码，无需填写主控地址。",
                f"Relay mode: auto-connect via public MQTT broker, only the invite code is needed."))
            self.hostLabel.hide()
            self.hostEdit.hide()
        else:
            self.nodeRelayHint.setText(L(
                "直连模式：请填写主控的 IP 地址和端口。",
                "Direct mode: enter the host's IP address and port."))
            self.hostLabel.show()
            self.hostEdit.show()

    def _gen_invite(self):
        use_relay = self._is_relay_mode()
        code = collab_server.generate_invite(self.maxNodesSpin.value(), use_relay=use_relay)
        self._last_code = code
        self.inviteBtn.setText(code)
        self.pushStartBtn.setEnabled(True)
        self.pushStopBtn.setEnabled(True)

        if use_relay:
            relay_addr = collab_server.relay_addr_display()
            self._server_log(L(f"已生成邀请码 {code}（中继模式，通过 {relay_addr} 中转）",
                               f"Invite generated: {code} (relay via {relay_addr})"))
        else:
            self._server_log(L("已生成邀请码，正在探测外网连通性…", "Invite generated; probing WAN connectivity…"))
            self.addrLabel.setText(L("正在探测公网 IP、UPnP 映射与防火墙…（约数秒）",
                                     "Detecting public IP, UPnP mapping & firewall… (a few seconds)"))
            threading.Thread(target=self._probe_net, daemon=True).start()
        log.info("生成协同邀请码")

    def _probe_net(self):
        """后台线程：探测公网 IP + UPnP 自动端口映射 + 防火墙放行。"""
        from app.services.network import (add_firewall_rule, get_lan_ip,
                                          get_public_ip, upnp_map)
        lan = get_lan_ip()
        pub = get_public_ip()
        fw_ok = add_firewall_rule()
        up_ok, up_info = upnp_map()
        self._net_info_ready.emit({
            "lan": lan, "pub": pub, "fw": fw_ok,
            "up": up_ok, "up_ip": up_info if up_ok else None,
        })

    def _on_net_info(self, d):
        pub, lan = d["pub"], d["lan"]
        lines = []
        is_v6 = bool(pub) and ":" in pub
        if d["up"]:
            ext = d["up_ip"] or pub
            self._pub_addr = f"[{ext}]:{PORT}" if ":" in ext else f"{ext}:{PORT}"
            lines.append(L(f"外网地址（UPnP 已自动映射）：{self._pub_addr}  ← 外网节点连这个",
                           f"WAN address (UPnP auto-mapped): {self._pub_addr}  ← for WAN nodes"))
        elif pub and is_v6:
            self._pub_addr = f"[{pub}]:{PORT}"
            lines.append(L(f"外网地址（IPv6，无需端口映射，直连可用）：{self._pub_addr}  ← 外网节点连这个",
                           f"WAN address (IPv6, no port mapping needed): {self._pub_addr}  ← for WAN nodes"))
        elif pub:
            self._pub_addr = f"{pub}:{PORT}"
            lines.append(L(f"公网 IP：{self._pub_addr}（IPv4，需在路由器转发 TCP {PORT} 到本机，或使用中继模式）",
                           f"Public IP: {self._pub_addr} (IPv4; forward TCP {PORT} on router, or use Relay mode)"))
        else:
            self._pub_addr = ""
            lines.append(L("无法探测公网 IP（建议切换到中继模式）",
                           "Cannot detect public IP (consider switching to Relay mode)"))
        self._lan_addr = f"{lan}:{PORT}"
        lines.append(L(f"局域网地址：{self._lan_addr}  ← 内网节点连这个",
                       f"LAN address: {self._lan_addr}  ← for LAN nodes"))
        if d["fw"]:
            self.adminBtn.hide()
            lines.append(L(f"防火墙：已放行 TCP {PORT}", f"Firewall: TCP {PORT} allowed"))
        else:
            self.adminBtn.show()
            lines.append(L(f"防火墙：尚未放行 TCP {PORT}，点击下方按钮以管理员身份重启后自动放行",
                           f"Firewall: TCP {PORT} not allowed yet; click the button below to elevate"))
        self.addrLabel.setText("\n".join(lines))

    def _restart_as_admin(self):
        """通过 UAC 以管理员身份重启本程序，以自动放行防火墙。"""
        import ctypes
        import os
        import sys
        try:
            params = f'"{os.path.abspath(sys.argv[0])}"'
            ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            if ret > 32:
                log.info("请求管理员权限重启以放行防火墙。")
                QGuiApplication.quit()
            else:
                InfoBar.warning(L("未授权", "Not elevated"),
                                L("您拒绝了 UAC 授权，防火墙未能放行", "UAC denied; firewall not opened"),
                                parent=self.window())
        except Exception as e:
            InfoBar.error(L("失败", "Failed"), str(e), parent=self.window())

    def _copy_invite(self):
        code = getattr(self, "_last_code", None)
        if not code:
            return
        QGuiApplication.clipboard().setText(code)
        InfoBar.success(L("已复制", "Copied"),
                        L(f"邀请码 {code} 已复制到剪贴板", f"Invite code {code} copied to clipboard"),
                        parent=self.window())

    def _copy_public(self):
        addr = getattr(self, "_pub_addr", "")
        if not addr:
            InfoBar.warning(L("暂无", "Unavailable"), L("尚未生成外网地址", "No WAN address yet"),
                            parent=self.window())
            return
        QGuiApplication.clipboard().setText(addr)
        InfoBar.success(L("已复制", "Copied"), addr, parent=self.window())

    def _copy_lan(self):
        addr = getattr(self, "_lan_addr", "")
        if not addr:
            return
        QGuiApplication.clipboard().setText(addr)
        InfoBar.success(L("已复制", "Copied"), addr, parent=self.window())

    def _push_start(self):
        stress = self.window().stress
        target_raw = stress.targetEdit.toPlainText().strip().splitlines()[0].strip()
        from app.services.auth import normalize_host
        host = normalize_host(target_raw)
        if not host:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请先在压测页填写目标", "Set the target on the Stress page first"),
                            parent=self.window())
            return
        config = {
            "target": host,
            "port": stress.portSpin.value(),
            "protocol": stress.protoCombo.currentText(),
            "url": "",
            "threads": stress.threadSpin.value(),
            "duration": stress.get_duration_seconds(),
            "rate": stress.rateSpin.value(),
            "packet_size": 64,
            "timeout": 5000,
            "headers": {},
        }
        if config["protocol"] in ("HTTP", "HTTPS"):
            config["url"] = target_raw if target_raw.startswith("http") else f"{config['protocol'].lower()}://{host}"
        collab_server.broadcast({"type": "start", "config": config})
        self._server_log(L(f"已广播开始: {config['protocol']}://{host}:{config['port']}",
                           f"Start broadcast: {config['protocol']}://{host}:{config['port']}"))
        log.info("广播协同开始")

    def _join(self):
        use_relay = self._is_relay_mode()
        code = self.codeEdit.text().strip()
        name = self.nameEdit.text().strip() or "node"
        host = self.hostEdit.text().strip()

        if not code:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请填写邀请码", "Invite code required"),
                            parent=self.window())
            return
        if not use_relay and not host:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请填写主控地址", "Host address required"),
                            parent=self.window())
            return

        ok, msg = collab_client.join(host, code, name, use_relay=use_relay)
        if ok:
            self.joinBtn.setEnabled(False)
            self.leaveBtn.setEnabled(True)
            self.connCombo.setEnabled(False)
            self.roleCombo.setEnabled(False)
            self._client_log(L(f"已加入，邀请码 {code}", f"Joined with code {code}"))
            log.info(f"加入协同: code={code} relay={use_relay}")
        else:
            InfoBar.error(L("加入失败", "Join failed"), msg, parent=self.window())

    def _leave(self):
        collab_client.leave()
        self.joinBtn.setEnabled(True)
        self.leaveBtn.setEnabled(False)
        self.connCombo.setEnabled(True)
        self.roleCombo.setEnabled(True)
        self._client_log(L("已退出", "Left"))

    def _on_remote_start(self, config):
        """收到主控开始指令：自动填充压测页配置并启动。"""
        self._client_log(L("收到主控指令，开始压测", "Received host command; starting"))
        stress = self.window().stress
        target = config.get("url") or config.get("target", "")
        if target:
            stress.targetEdit.setPlainText(target)
        port = config.get("port", 80)
        stress.portSpin.setValue(port)
        proto = config.get("protocol", "HTTP")
        idx = stress.protoCombo.findText(proto)
        if idx >= 0:
            stress.protoCombo.setCurrentIndex(idx)
        threads = config.get("threads", 8)
        stress.threadSpin.setValue(threads)
        stress.threadSlider.setValue(threads)
        rate = config.get("rate", 100)
        stress.rateSpin.setValue(rate)
        engine.start([config])

    def _on_local_snapshot(self, d):
        """本地压测快照：节点端保存用于周期上报。"""
        self._local_stats = {
            "total": d.get("total", 0),
            "success": d.get("success", 0),
            "fail": d.get("fail", 0),
            "qps": d.get("qps", 0.0),
        }

    def _tick_stats(self):
        """每秒：节点上报本地统计，主控刷新聚合显示。"""
        # 节点侧：如果已连接，上报当前统计
        if collab_client.connected:
            collab_client.send_stats(self._local_stats)

        # 主控侧：只要房间处于活跃状态就刷新（邀请码过期只阻止新节点加入，不影响已连接节点）
        if collab_server.active:
            self._update_node_stats()

    def _update_node_stats(self):
        """主控端：聚合所有节点统计并更新 UI。"""
        nodes = collab_server.get_nodes()
        total_req = 0
        total_ok = 0
        total_qps = 0.0
        parts = []
        for name, stats in nodes:
            if stats:
                total_req += stats.get("total", 0)
                total_ok += stats.get("success", 0)
                total_qps += stats.get("qps", 0.0)
                parts.append(f"{name}: ✓{stats.get('success',0)} ✗{stats.get('fail',0)} ({stats.get('qps',0):.0f} QPS)")
            else:
                parts.append(f"{name}: " + L("等待中...", "waiting..."))
        self.mTotal.setText(str(total_req))
        self.mSuccess.setText(str(total_ok))
        self.mQps.setText(f"{total_qps:.1f}")
        if parts:
            self.nodeListLabel.setText("  |  ".join(parts))
        else:
            self.nodeListLabel.setText(L("（暂无节点连接）", "(no nodes connected)"))

    def _server_log(self, msg):
        self._append_log(msg)

    def _client_log(self, msg):
        self._append_log(msg)

    def _append_log(self, msg):
        self._log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self._log_lines = self._log_lines[-30:]
        self.logLabel.setText("\n".join(self._log_lines))

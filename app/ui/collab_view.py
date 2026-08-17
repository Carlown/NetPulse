"""协同测试页：主控邀请 / 节点加入。"""
import threading

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget
from qfluentwidgets import (BodyLabel, CaptionLabel, ComboBox, InfoBar,
                            InfoBarPosition, LineEdit, PrimaryPushButton,
                            PushButton, ScrollArea, SimpleCardWidget, SpinBox,
                            StrongBodyLabel, SubtitleLabel, SwitchButton)

from app.services.collab import collab_client, collab_server
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

        root = QVBoxLayout(self.view)
        root.setContentsMargins(36, 24, 36, 24)
        root.setSpacing(16)

        root.addWidget(SubtitleLabel(L("协同测试", "Collaborative Testing"), self.view))

        role_row = QHBoxLayout()
        role_row.addWidget(BodyLabel(L("模式", "Mode"), self.view))
        self.roleCombo = ComboBox(self.view)
        self.roleCombo.addItems([L("主控（发起邀请）", "Host (invite)"), L("节点（加入）", "Node (join)")])
        self.roleCombo.currentIndexChanged.connect(self._switch_role)
        role_row.addWidget(self.roleCombo)
        role_row.addStretch(1)
        root.addLayout(role_row)

        cols = QHBoxLayout()
        cols.setSpacing(16)

        # 主控卡片
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
        self.inviteHint = CaptionLabel(L("↑ 点击邀请码即复制；5 分钟内有效。支持局域网与外网节点。",
                                         "↑ Click the code to copy; valid 5 min. LAN & WAN nodes supported."), self.hostCard)
        self.inviteHint.setWordWrap(True)
        hl.addWidget(self.inviteHint)

        # 连接地址（外网/内网）与一键复制
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

        # 节点卡片
        self.nodeCard = SimpleCardWidget(self.view)
        nl = QVBoxLayout(self.nodeCard)
        nl.setContentsMargins(20, 16, 20, 16)
        nl.setSpacing(10)
        nl.addWidget(StrongBodyLabel(L("加入协同", "Join a Session"), self.nodeCard))
        nl.addWidget(BodyLabel(L("主控地址（内网或公网 IP，可带端口）", "Host address (LAN/WAN IP, port optional)"), self.nodeCard))
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

        # 节点统计
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
        collab_client.status_msg.connect(lambda m: self._client_log(m))
        collab_client.start_requested.connect(self._on_remote_start)
        collab_client.stop_requested.connect(lambda: engine.stop())

        self._switch_role(0)

    def _mini(self, title, value_label):
        w = QWidget(self.view)
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)
        v.addWidget(CaptionLabel(title, w))
        v.addWidget(value_label)
        return w

    def _switch_role(self, idx):
        self.hostCard.setVisible(idx == 0)
        self.nodeCard.setVisible(idx == 1)

    def _gen_invite(self):
        code = collab_server.generate_invite(self.maxNodesSpin.value())
        self._last_code = code
        self.inviteBtn.setText(code)
        self.pushStartBtn.setEnabled(True)
        self.pushStopBtn.setEnabled(True)
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
        from app.services.collab import PORT
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
            lines.append(L(f"公网 IP：{self._pub_addr}（IPv4，需在路由器转发 TCP {PORT} 到本机，或用 IPv6）",
                           f"Public IP: {self._pub_addr} (IPv4; forward TCP {PORT} on router, or use IPv6)"))
        else:
            self._pub_addr = ""
            lines.append(L("无法探测公网 IP（本机可能无外网连接）",
                           "Failed to detect public IP (no WAN connection?)"))
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
        target_raw = stress.targetEdit.text().strip()
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
        host = self.hostEdit.text().strip()
        code = self.codeEdit.text().strip()
        name = self.nameEdit.text().strip() or "node"
        if not host or not code:
            InfoBar.warning(L("参数错误", "Invalid input"),
                            L("请填写主控地址与邀请码", "Host address and invite code required"),
                            parent=self.window())
            return
        ok, msg = collab_client.join(host, code, name)
        if ok:
            self.joinBtn.setEnabled(False)
            self.leaveBtn.setEnabled(True)
            self._client_log(L(f"已加入 {host}", f"Joined {host}"))
            log.info(f"加入协同: {host}")
        else:
            InfoBar.error(L("加入失败", "Join failed"), msg, parent=self.window())

    def _leave(self):
        collab_client.leave()
        self.joinBtn.setEnabled(True)
        self.leaveBtn.setEnabled(False)
        self._client_log(L("已退出", "Left"))

    def _on_remote_start(self, config):
        self._client_log(L("收到主控指令，开始压测", "Received host command; starting"))
        engine.start(config)

    _log_lines = []

    def _server_log(self, msg):
        self._append_log(msg)

    def _client_log(self, msg):
        self._append_log(msg)

    def _append_log(self, msg):
        import time
        self._log_lines.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        self._log_lines = self._log_lines[-30:]
        self.logLabel.setText("\n".join(self._log_lines))

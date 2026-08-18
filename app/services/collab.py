"""协同测试：直连模式（TCP）+ 中继模式（MQTT 公共服务器，零配置开箱即用）

直连模式：主控监听本地 TCP 端口，节点直连（适用于局域网）。
中继模式：通过公共 MQTT 消息服务器中转，支持外网节点加入，无需部署任何服务器，无需公网 IP。
"""
import json
import random
import socket
import string
import threading
import time
import uuid

from PySide6.QtCore import QObject, Signal, QTimer

from app.services.settings import settings
from app.ui.i18n import L

PORT = 50505

# MQTT 公共中继配置 - 使用 HiveMQ 免费公共服务器（WebSocket 端口，防火墙友好）
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 8000  # WebSocket 端口
MQTT_TRANSPORT = "websockets"
MQTT_TOPIC_PREFIX = "netpulse/v1/"


def _gen_code(length=8):
    """生成邀请码（去掉易混淆字符）。"""
    alphabet = string.ascii_uppercase.replace("O", "").replace("I", "") + string.digits.replace("0", "").replace("1", "")
    return "".join(random.choices(alphabet, k=length))


def _topic_host(code):
    return f"{MQTT_TOPIC_PREFIX}{code}/host"


def _topic_node(code):
    return f"{MQTT_TOPIC_PREFIX}{code}/node"


def _connect_tcp(host, port, timeout=8):
    """创建 TCP 连接（支持 IPv4/IPv6/域名解析）。"""
    infos = socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM)
    last_err = None
    for family, socktype, proto, canonname, sockaddr in infos:
        s = socket.socket(family, socktype, proto)
        s.settimeout(timeout)
        try:
            s.connect(sockaddr)
            return s
        except OSError as e:
            last_err = e
            try:
                s.close()
            except OSError:
                pass
    raise last_err if last_err else OSError(f"无法连接到 {host}:{port}")


def _parse_host_port(host_str, default_port=PORT):
    """解析 host:port 格式，支持 [IPv6]:port。"""
    if host_str.startswith("[") and "]" in host_str:
        inside, _, rest = host_str.partition("]")
        host = inside.strip("[")
        p = rest.lstrip(":")
        port = int(p) if p.isdigit() else default_port
        return host, port
    elif host_str.count(":") == 1 and not host_str.replace(".", "").replace(":", "").isalpha():
        h, _, p = host_str.rpartition(":")
        if p.isdigit() and 0 < int(p) < 65536:
            return h, int(p)
    return host_str, default_port


# ========== 直连模式 TCP 服务端 ==========

class CollabServer(QObject):
    log_msg = Signal(str)
    nodes_changed = Signal()

    def __init__(self):
        super().__init__()
        self._sessions = {}   # sid -> {sock, name, stats}
        self._lock = threading.Lock()
        self._code = None
        self._expiry = 0.0
        self._max_nodes = 0
        self._listen_sock = None
        self.active = False
        # MQTT 中继模式
        self._mqtt_client = None
        self._relay_nodes = {}  # node_id -> {"name", "stats"}
        self._relay_mode = False
        self._relay_connected = False

    @property
    def invite_valid(self):
        return self._code and time.time() < self._expiry

    @property
    def relay_mode(self):
        return self._relay_mode

    # ---------- 公开 API ----------

    def generate_invite(self, max_nodes: int, use_relay: bool = False) -> str:
        """生成邀请码。use_relay=True 使用 MQTT 中继，False 使用 TCP 直连。"""
        self.shutdown()

        self._max_nodes = max(1, max_nodes)
        self._code = _gen_code(8 if use_relay else 6)
        self._expiry = time.time() + 300  # 5分钟有效期
        self._relay_mode = use_relay

        if use_relay:
            self._start_relay_host()
        else:
            self._start_listen()
        return self._code

    def broadcast(self, obj):
        """广播消息给所有已连接节点。"""
        if self._relay_mode:
            self._relay_broadcast(obj)
        else:
            with self._lock:
                socks = [v["sock"] for v in self._sessions.values()]
            msg = (json.dumps(obj) + "\n").encode("utf-8")
            for s in socks:
                try:
                    s.sendall(msg)
                except OSError:
                    pass

    def get_nodes(self):
        """返回 [(name, stats|None), ...]"""
        if self._relay_mode:
            with self._lock:
                return [(v["name"], dict(v["stats"]) if v["stats"] else None)
                        for v in self._relay_nodes.values()]
        else:
            with self._lock:
                return [(v["name"], dict(v["stats"]) if v["stats"] else None)
                        for v in self._sessions.values()]

    def shutdown(self):
        """关闭所有连接和监听。"""
        self.active = False
        # MQTT 中继先清理（需要 self._code 来发送房间关闭通知）
        self._cleanup_relay()
        self._code = None
        # TCP 直连
        if self._listen_sock:
            try:
                self._listen_sock.close()
            except OSError:
                pass
            self._listen_sock = None
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for v in sessions:
            try:
                v["sock"].close()
            except OSError:
                pass

    def relay_addr_display(self):
        return L("公共 MQTT 中继 (broker.hivemq.com)",
                 "Public MQTT relay (broker.hivemq.com)")

    # ---------- TCP 直连内部 ----------

    def _start_listen(self):
        for family, bind_addr in ((socket.AF_INET6, "::"), (socket.AF_INET, "0.0.0.0")):
            try:
                s = socket.socket(family, socket.SOCK_STREAM)
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                if family == socket.AF_INET6:
                    try:
                        s.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
                    except OSError:
                        pass
                s.bind((bind_addr, PORT))
                s.listen(16)
                s.settimeout(1.0)
                self._listen_sock = s
                self.active = True
                threading.Thread(target=self._accept_loop, daemon=True).start()
                return
            except OSError as e:
                last_err = e
                try:
                    s.close()
                except OSError:
                    pass
        self.log_msg.emit(L(f"监听失败: {last_err}", f"Listen failed: {last_err}"))

    def _accept_loop(self):
        while self.active and not self._relay_mode:
            try:
                conn, addr = self._listen_sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()

    def _client_loop(self, conn, addr):
        conn.settimeout(600)
        sid = f"{addr[0]}:{addr[1]}"
        f = conn.makefile("r", encoding="utf-8")
        try:
            for line in f:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                t = msg.get("type")
                if t == "join":
                    with self._lock:
                        ok = (msg.get("code") == self._code and self.invite_valid
                              and len(self._sessions) < self._max_nodes)
                        if ok:
                            self._sessions[sid] = {"sock": conn, "name": msg.get("name") or sid, "stats": None}
                    try:
                        conn.sendall(b'{"type":"joined"}\n')
                    except OSError:
                        break
                    if ok:
                        name = msg.get('name') or sid
                        self.log_msg.emit(L(f"节点 {name} 已加入", f"Node {name} joined"))
                        self.nodes_changed.emit()
                    else:
                        break
                elif t == "stats":
                    with self._lock:
                        if sid in self._sessions:
                            self._sessions[sid]["stats"] = msg.get("stats")
                    self.nodes_changed.emit()
                elif t == "leave":
                    break
        except OSError:
            pass
        finally:
            with self._lock:
                self._sessions.pop(sid, None)
            self.nodes_changed.emit()
            try:
                conn.close()
            except OSError:
                pass

    # ---------- MQTT 中继内部 ----------

    def _start_relay_host(self):
        """通过 MQTT 中继创建房间。"""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self.log_msg.emit(L("错误：缺少 paho-mqtt 库，请运行 pip install paho-mqtt",
                                "Error: paho-mqtt missing, run: pip install paho-mqtt"))
            return

        client_id = f"netpulse_host_{uuid.uuid4().hex[:12]}"
        self._mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            transport=MQTT_TRANSPORT
        )

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                self._relay_connected = True
                self.active = True
                client.subscribe(_topic_host(self._code), qos=1)
                relay_addr = self.relay_addr_display()
                self.log_msg.emit(L(f"中继模式已就绪，邀请码 {self._code}（通过 {relay_addr}）",
                                    f"Relay ready, invite code {self._code} (via {relay_addr})"))
                self.nodes_changed.emit()
            else:
                self.log_msg.emit(L(f"中继连接失败: {reason_code}", f"Relay connection failed: {reason_code}"))

        def on_message(client, userdata, msg):
            """处理节点发来的消息。"""
            try:
                data = json.loads(msg.payload.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return

            mtype = data.get("type")
            if mtype == "join":
                node_id = data.get("node_id", str(uuid.uuid4())[:8])
                name = (data.get("name") or node_id)[:32]
                with self._lock:
                    if not self.invite_valid:
                        client.publish(_topic_node(self._code), json.dumps({
                            "type": "error", "to": node_id, "code": "code_expired"
                        }), qos=1)
                        return
                    if len(self._relay_nodes) >= self._max_nodes:
                        # 房间已满，发送错误代码
                        client.publish(_topic_node(self._code), json.dumps({
                            "type": "error", "to": node_id, "code": "room_full"
                        }), qos=1)
                        return
                    self._relay_nodes[node_id] = {"name": name, "stats": None}
                # 通知节点加入成功
                client.publish(_topic_node(self._code), json.dumps({
                    "type": "joined", "to": node_id, "node_id": node_id
                }), qos=1)
                self.log_msg.emit(L(f"节点 {name} 已加入", f"Node {name} joined"))
                self.nodes_changed.emit()
            elif mtype == "stats":
                node_id = data.get("node_id")
                with self._lock:
                    if node_id in self._relay_nodes:
                        self._relay_nodes[node_id]["stats"] = data.get("stats")
                self.nodes_changed.emit()
            elif mtype == "leave":
                node_id = data.get("node_id")
                with self._lock:
                    node = self._relay_nodes.pop(node_id, None)
                if node:
                    self.log_msg.emit(L(f"节点 {node['name']} 已退出", f"Node {node['name']} left"))
                    self.nodes_changed.emit()

        def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
            self._relay_connected = False
            if self._relay_mode:
                self.log_msg.emit(L("与中继服务器断开连接", "Disconnected from relay server"))
                with self._lock:
                    self._relay_nodes.clear()
                self.nodes_changed.emit()

        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_message = on_message
        self._mqtt_client.on_disconnect = on_disconnect

        try:
            self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self._mqtt_client.loop_start()
            self.log_msg.emit(L("正在连接公共中继服务器...", "Connecting to public relay server..."))
        except Exception as e:
            self.log_msg.emit(L(f"中继连接失败: {e}", f"Relay connection failed: {e}"))

    def _relay_broadcast(self, obj):
        if self._mqtt_client and self._relay_connected:
            try:
                self._mqtt_client.publish(_topic_node(self._code), json.dumps(obj), qos=1)
            except Exception:
                pass

    def _cleanup_relay(self):
        """清理 MQTT 中继连接。"""
        self._relay_connected = False
        if self._mqtt_client:
            try:
                # 广播房间关闭
                if self._code:
                    self._mqtt_client.publish(_topic_node(self._code),
                                              json.dumps({"type": "room_closed"}), qos=1)
                    # 给后台线程一点时间发送消息（避免 publish 后立刻 disconnect 导致消息丢失）
                    time.sleep(0.2)
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
            self._mqtt_client = None
        with self._lock:
            self._relay_nodes.clear()


# ========== 客户端（节点） ==========

class CollabClient(QObject):
    log_msg = Signal(str)
    status_msg = Signal(str)
    start_requested = Signal(dict)
    stop_requested = Signal()

    def __init__(self):
        super().__init__()
        # TCP 直连
        self._sock = None
        self.connected = False
        # MQTT 中继
        self._mqtt_client = None
        self._relay_mode = False
        self._relay_connected = False
        self._relay_code = None
        self._relay_node_id = None
        self._relay_name = None
        self._join_result = None  # (success: bool, msg: str)
        self._join_event = None

    def join(self, host: str, code: str, name: str, use_relay: bool = False):
        """加入协同测试。"""
        try:
            if use_relay:
                return self._join_relay(code, name)
            else:
                return self._join_direct(host, code, name)
        except Exception as e:
            return False, L(f"连接失败: {e}", f"Connection failed: {e}")

    def _join_direct(self, host: str, code: str, name: str):
        """TCP 直连模式加入。"""
        host_clean, port = _parse_host_port(host, PORT)
        s = _connect_tcp(host_clean, port, timeout=8)
        s.sendall((json.dumps({"type": "join", "code": code.strip().upper(), "name": name}) + "\n").encode("utf-8"))
        s.settimeout(10)
        f = s.makefile("r", encoding="utf-8")
        line = f.readline()
        resp = json.loads(line) if line else {}
        if resp.get("type") != "joined":
            s.close()
            return False, L("邀请码无效或已满员", "Invalid code or room full")
        self._sock = s
        self.connected = True
        self._relay_mode = False
        threading.Thread(target=self._read_tcp_loop, args=(s, f), daemon=True).start()
        return True, L("已加入", "Joined")

    def _join_relay(self, code: str, name: str):
        """MQTT 中继模式加入。"""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            return False, L("错误：缺少 paho-mqtt 库", "Error: paho-mqtt missing")

        code = code.strip().upper()
        self._relay_code = code
        self._relay_name = name
        self._relay_node_id = uuid.uuid4().hex[:12]
        self._relay_mode = True
        self._join_result = None
        self._join_event = threading.Event()

        client_id = f"netpulse_node_{uuid.uuid4().hex[:12]}"
        self._mqtt_client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            transport=MQTT_TRANSPORT
        )

        def on_connect(client, userdata, flags, reason_code, properties):
            if reason_code == 0:
                client.subscribe(_topic_node(code), qos=1)
                # 发送加入请求
                client.publish(_topic_host(code), json.dumps({
                    "type": "join",
                    "code": code,
                    "name": name,
                    "node_id": self._relay_node_id
                }), qos=1)
            else:
                self._join_result = (False, L(f"连接失败: {reason_code}", f"Connection failed: {reason_code}"))
                self._join_event.set()

        def on_message(client, userdata, msg):
            try:
                data = json.loads(msg.payload.decode())
            except (json.JSONDecodeError, UnicodeDecodeError):
                return

            to = data.get("to")
            # 如果消息指定了接收者，只处理发给自己的
            if to is not None and to != self._relay_node_id:
                return

            mtype = data.get("type")
            if mtype == "joined":
                self._relay_connected = True
                self.connected = True
                self._join_result = (True, L("已加入（中继模式）", "Joined (relay mode)"))
                self._join_event.set()
                self.status_msg.emit(L("已加入（公共中继模式）", "Joined (public relay mode)"))
            elif mtype == "error":
                err_code = data.get("code", "")
                err_map = {
                    "room_full": L("房间已满", "Room full"),
                    "code_expired": L("邀请码已过期", "Invite code expired"),
                    "invalid_code": L("邀请码无效", "Invalid invite code"),
                }
                err = err_map.get(err_code, L("加入失败", "Join failed"))
                self._join_result = (False, err)
                self._join_event.set()
                self.status_msg.emit(L(f"加入失败: {err}", f"Join failed: {err}"))
                self._cleanup_relay()
            elif mtype == "start" and self._relay_connected:
                self.start_requested.emit(data.get("config") or {})
            elif mtype == "stop" and self._relay_connected:
                self.stop_requested.emit()
            elif mtype == "room_closed" and self._relay_connected:
                self.status_msg.emit(L("主控已关闭房间", "Host closed the room"))
                self._cleanup_relay()

        def on_disconnect(client, userdata, disconnect_flags, reason_code, properties):
            if self._relay_connected:
                self.status_msg.emit(L("与中继服务器断开连接", "Disconnected from relay server"))
            self._relay_connected = False
            self.connected = False

        self._mqtt_client.on_connect = on_connect
        self._mqtt_client.on_message = on_message
        self._mqtt_client.on_disconnect = on_disconnect

        try:
            self._mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
            self._mqtt_client.loop_start()
        except Exception as e:
            self._cleanup_relay()
            return False, L(f"连接失败: {e}", f"Connection failed: {e}")

        # 等待加入结果（最多 10 秒）
        if self._join_event.wait(timeout=10):
            ok, msg = self._join_result
            if ok:
                return True, msg
            else:
                self._cleanup_relay()
                return False, msg
        else:
            self._cleanup_relay()
            return False, L("连接超时", "Connection timeout")

    def _cleanup_relay(self):
        self._relay_connected = False
        self.connected = False
        if self._mqtt_client:
            try:
                if self._relay_code and self._relay_node_id:
                    self._mqtt_client.publish(_topic_host(self._relay_code), json.dumps({
                        "type": "leave",
                        "node_id": self._relay_node_id
                    }), qos=1)
                    # 给后台线程一点时间发送离开消息
                    time.sleep(0.15)
                self._mqtt_client.loop_stop()
                self._mqtt_client.disconnect()
            except Exception:
                pass
            self._mqtt_client = None
        self._relay_code = None
        self._relay_node_id = None
        self._relay_name = None
        self._relay_mode = False

    def _read_tcp_loop(self, sock, f):
        """TCP 直连模式读取消息。"""
        try:
            for line in f:
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                t = msg.get("type")
                if t == "start":
                    self.start_requested.emit(msg.get("config") or {})
                elif t == "stop":
                    self.stop_requested.emit()
                elif t == "close":
                    break
        except OSError:
            pass
        finally:
            self.connected = False
            self.status_msg.emit(L("与主控断开连接", "Disconnected from host"))
            try:
                sock.close()
            except OSError:
                pass

    def send_stats(self, stats: dict):
        """上报压测统计数据给主控。"""
        msg_json = json.dumps({"type": "stats", "stats": stats, "node_id": self._relay_node_id})
        if self._relay_mode and self._mqtt_client and self._relay_connected:
            try:
                self._mqtt_client.publish(_topic_host(self._relay_code), msg_json, qos=1)
            except Exception:
                pass
        elif self._sock and self.connected:
            try:
                self._sock.sendall((msg_json + "\n").encode("utf-8"))
            except OSError:
                pass

    def leave(self):
        """退出协同。"""
        if self._relay_mode:
            self._cleanup_relay()
        else:
            if self._sock:
                try:
                    self._sock.sendall((json.dumps({"type": "leave"}) + "\n").encode("utf-8"))
                    self._sock.close()
                except OSError:
                    pass
                self._sock = None
        self.connected = False


collab_server = CollabServer()
collab_client = CollabClient()

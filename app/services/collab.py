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
    raise last_err if last_err else OSError(L(f"无法连接到 {host}:{port}", f"Cannot connect to {host}:{port}"))


def _parse_host_port(host_str, default_port=PORT):
    """解析 host:port 格式，支持 [IPv6]:port。"""
    host_str = (host_str or "").strip()
    if not host_str:
        raise ValueError("host is required")
    if host_str.startswith("[") and "]" in host_str:
        inside, _, rest = host_str.partition("]")
        if not inside or (rest and not rest.startswith(":")):
            raise ValueError("invalid bracketed host")
        host = inside.strip("[")
        if not host:
            raise ValueError("host is required")
        p = rest.lstrip(":")
        if not p:
            # A trailing colon is almost always a typo.  Accept the omitted
            # port (`[::1]`) but reject the malformed `[::1]:` form.
            if rest:
                raise ValueError("port must be between 1 and 65535")
            port = default_port
        elif not p.isdigit() or not 0 < int(p) < 65536:
            raise ValueError("port must be between 1 and 65535")
        else:
            port = int(p)
        return host, port
    if host_str.count(":") == 1:
        # A single colon is the host:port form.  Do not silently treat an
        # invalid port as part of the hostname; that caused confusing DNS
        # errors for inputs such as `server:abc`.
        host, _, port_text = host_str.rpartition(":")
        if not host or not port_text.isdigit() or not 0 < int(port_text) < 65536:
            raise ValueError("port must be between 1 and 65535")
        return host, int(port_text)
    # Unbracketed IPv6 contains multiple colons.  It has no unambiguous port;
    # use the default and let getaddrinfo validate the address.
    return host_str, default_port


def _enable_tcp_keepalive(sock, idle_sec=60, interval_sec=30, count=3):
    """启用 TCP keepalive，防止空闲连接被网络设备断开。"""
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        # Windows 和 Linux/macOS 的 TCP keepalive 选项
        if hasattr(socket, 'TCP_KEEPIDLE'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, idle_sec)
        if hasattr(socket, 'TCP_KEEPINTVL'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        if hasattr(socket, 'TCP_KEEPCNT'):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, count)
        # Windows 特定的 SIO_KEEPALIVE_VALS
        try:
            import struct
            # SIO_KEEPALIVE_VALS = 0x98000004 (WSAIoctl)
            idle_ms = idle_sec * 1000
            interval_ms = interval_sec * 1000
            sock.ioctl(0x98000004, struct.pack('IIII', 1, idle_ms, interval_ms))
        except Exception:
            pass
    except (OSError, AttributeError):
        pass


# ========== 直连模式 TCP 服务端 ==========

class CollabServer(QObject):
    log_msg = Signal(str)
    nodes_changed = Signal()
    relay_status_changed = Signal(bool)  # True=已连接, False=断开/失败

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
        self._gen = 0  # 邀请码代数：每次生成/关闭递增，用于让过期的MQTT后台线程失效（防快速切换模式时崩溃）
        self._mqtt_cleanup_done = threading.Event()
        self._mqtt_cleanup_done.set()  # 初始状态：无待清理的客户端

    @property
    def invite_valid(self):
        return self._code and time.time() < self._expiry

    def invite_remaining_seconds(self):
        """返回邀请码剩余有效秒数，-1 表示没有活跃房间。"""
        if not self._code:
            return -1
        return max(0, int(self._expiry - time.time()))

    @property
    def relay_mode(self):
        return self._relay_mode

    # ---------- 公开 API ----------

    def generate_invite(self, max_nodes: int, use_relay: bool = False) -> str:
        """生成邀请码。use_relay=True 使用 MQTT 中继，False 使用 TCP 直连。"""
        self.shutdown()

        self._gen += 1  # 代数+1：使残留的旧MQTT后台线程（连接中/清理中）全部失效
        gen = self._gen
        self._max_nodes = max(1, max_nodes)
        self._code = _gen_code(8 if use_relay else 6)
        self._expiry = time.time() + 300  # 5分钟有效期
        self._relay_mode = use_relay

        if use_relay:
            # MQTT 连接放到后台线程，不阻塞 UI
            threading.Thread(target=self._start_relay_host, args=(gen,), daemon=True).start()
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
        self._gen += 1  # 使残留的MQTT后台线程全部失效
        self.active = False
        self._relay_mode = False
        self._relay_connected = False  # 重置中继连接状态，避免残留旧状态
        # MQTT 中继先清理（需要 self._code 来发送房间关闭通知）
        # 把清理放到后台线程，避免阻塞 UI（sleep + disconnect 都是阻塞操作）
        old_client = self._mqtt_client
        old_code = self._code
        self._mqtt_client = None
        if old_client is not None:
            self._mqtt_cleanup_done.clear()
            def _async_cleanup():
                try:
                    try:
                        if old_code:
                            old_client.publish(_topic_node(old_code),
                                              json.dumps({"type": "room_closed"}), qos=1)
                            time.sleep(0.2)
                    except Exception:
                        pass
                    # 先 disconnect 再 loop_stop：让网络线程先收到断开通知再join，
                    # 降低与 loop_start 并发启停导致 C 层崩溃的概率
                    try:
                        old_client.disconnect()
                    except Exception:
                        pass
                    try:
                        old_client.loop_stop()
                    except Exception:
                        pass
                finally:
                    self._mqtt_cleanup_done.set()
            threading.Thread(target=_async_cleanup, daemon=True).start()
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
        with self._lock:
            self._relay_nodes.clear()

    def relay_addr_display(self):
        return L("公共 MQTT 中继 (broker.hivemq.com)",
                 "Public MQTT relay (broker.hivemq.com)")

    # ---------- TCP 直连内部 ----------

    def _start_listen(self):
        last_err = None
        for family, bind_addr in ((socket.AF_INET6, "::"), (socket.AF_INET, "0.0.0.0")):
            s = None
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
                if s:
                    try:
                        s.close()
                    except OSError:
                        pass
        self.log_msg.emit(L(f"监听失败: {last_err}", f"Listen failed: {last_err}"))

    def _accept_loop(self):
        while self.active and not self._relay_mode:
            # 取局部引用：shutdown 期间 _listen_sock 可能被置 None，避免 NoneType.accept 崩线程
            sock = self._listen_sock
            if sock is None:
                break
            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            threading.Thread(target=self._client_loop, args=(conn, addr), daemon=True).start()

    def _client_loop(self, conn, addr):
        conn.settimeout(600)
        _enable_tcp_keepalive(conn)
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
                    if ok:
                        try:
                            conn.sendall(b'{"type":"joined"}\n')
                        except OSError:
                            break
                        name = msg.get('name') or sid
                        self.log_msg.emit(L(f"节点 {name} 已加入", f"Node {name} joined"))
                        self.nodes_changed.emit()
                    else:
                        # 邀请码无效或房间已满：发送错误响应后断开
                        try:
                            conn.sendall(b'{"type":"error","msg":"invalid_code_or_full"}\n')
                        except OSError:
                            pass
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
                node = self._sessions.pop(sid, None)
            if node:
                self.log_msg.emit(L(f"节点 {node['name']} 已断开", f"Node {node['name']} disconnected"))
            self.nodes_changed.emit()
            try:
                conn.close()
            except OSError:
                pass

    # ---------- MQTT 中继内部 ----------

    def _start_relay_host(self, gen: int):
        """通过 MQTT 中继创建房间。gen 为本次生成的代数，失效则自清理退出。"""
        try:
            import paho.mqtt.client as mqtt
        except ImportError:
            self.log_msg.emit(L("错误：缺少 paho-mqtt 库，请运行 pip install paho-mqtt",
                                "Error: paho-mqtt missing, run: pip install paho-mqtt"))
            self.relay_status_changed.emit(False)  # 通知UI隐藏连接遮罩
            return

        # 等待旧 MQTT 客户端清理完成，避免并发启停 paho 线程导致 C 层崩溃
        # 加超时：即使旧清理线程异常卡住，也不能永久阻塞新连接（防止界面假死）
        self._mqtt_cleanup_done.wait(timeout=3.0)

        # 等待清理期间可能又切换了模式，再次检查代数是否有效
        if gen != self._gen:
            return

        client_id = f"netpulse_host_{uuid.uuid4().hex[:12]}"
        # 局部变量持有client：仅当代数校验通过（连接成功且未被新一次生成/关闭取代）才提交到 self._mqtt_client
        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=client_id,
            transport=MQTT_TRANSPORT
        )

        def on_connect(client, userdata, flags, reason_code, properties):
            if gen != self._gen:
                return  # 已被新的生成/关闭取代，忽略过期回调
            if reason_code == 0:
                self._relay_connected = True
                self.active = True
                client.subscribe(_topic_host(self._code), qos=1)
                relay_addr = self.relay_addr_display()
                self.log_msg.emit(L(f"中继模式已就绪，邀请码 {self._code}（通过 {relay_addr}）",
                                    f"Relay ready, invite code {self._code} (via {relay_addr})"))
                self.relay_status_changed.emit(True)
                self.nodes_changed.emit()
            else:
                self.log_msg.emit(L(f"中继连接失败: {reason_code}", f"Relay connection failed: {reason_code}"))
                self.relay_status_changed.emit(False)

        def on_message(client, userdata, msg):
            """处理节点发来的消息。"""
            if gen != self._gen:
                return  # 过期消息，忽略
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
            if gen != self._gen:
                return  # 过期断开事件（房间已被新的生成/关闭取代），不误清新房间状态
            if self._relay_connected:
                self._relay_connected = False
                if self._relay_mode:
                    self.log_msg.emit(L("与中继服务器断开连接", "Disconnected from relay server"))
                    with self._lock:
                        self._relay_nodes.clear()
                    self.nodes_changed.emit()
                self.relay_status_changed.emit(False)

        client.on_connect = on_connect
        client.on_message = on_message
        client.on_disconnect = on_disconnect

        try:
            client.connect(MQTT_BROKER, MQTT_PORT, 60)
            # connect 阻塞期间用户可能已再次切换模式：代数失效则自清理退出，
            # 不启动网络线程、不提交到实例（避免与 shutdown 的清理线程并发启停 paho 线程导致崩溃）
            if gen != self._gen:
                try:
                    client.disconnect()
                except Exception:
                    pass
                return
            client.loop_start()
            self._mqtt_client = client  # 代数有效，正式提交
            self.log_msg.emit(L("正在连接公共中继服务器...", "Connecting to public relay server..."))
        except Exception as e:
            if gen == self._gen:
                self.log_msg.emit(L(f"中继连接失败: {e}", f"Relay connection failed: {e}"))
                self.relay_status_changed.emit(False)

    def _relay_broadcast(self, obj):
        if self._mqtt_client and self._relay_connected:
            try:
                self._mqtt_client.publish(_topic_node(self._code), json.dumps(obj), qos=1)
            except Exception:
                pass


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
        self._mqtt_cleanup_done = threading.Event()
        self._mqtt_cleanup_done.set()  # 初始状态：无待清理的客户端

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
        # 加入成功：设置较长的读超时（10分钟），并启用 TCP keepalive 防止空闲断开
        s.settimeout(600)
        _enable_tcp_keepalive(s)
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

        # 等待旧 MQTT 客户端清理完成，避免并发启停 paho 线程导致 C 层崩溃
        # 加超时：即使旧清理线程异常卡住，也不能永久阻塞新连接（防止界面假死）
        self._mqtt_cleanup_done.wait(timeout=3.0)

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
        client = self._mqtt_client
        code = self._relay_code
        node_id = self._relay_node_id
        self._mqtt_client = None
        if client:
            self._mqtt_cleanup_done.clear()
            def _async_client_cleanup():
                try:
                    try:
                        if code and node_id:
                            client.publish(_topic_host(code), json.dumps({
                                "type": "leave",
                                "node_id": node_id
                            }), qos=1)
                            time.sleep(0.15)
                    except Exception:
                        pass
                    # 先 disconnect 再 loop_stop：降低 paho 网络线程并发启停崩溃风险
                    try:
                        client.disconnect()
                    except Exception:
                        pass
                    try:
                        client.loop_stop()
                    except Exception:
                        pass
                finally:
                    self._mqtt_cleanup_done.set()
            threading.Thread(target=_async_client_cleanup, daemon=True).start()
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
                elif t == "error":
                    err = msg.get("msg", "unknown_error")
                    err_map = {
                        "invalid_code_or_full": L("邀请码无效或房间已满", "Invalid code or room full"),
                    }
                    self.status_msg.emit(L(f"连接被拒绝: {err_map.get(err, err)}",
                                           f"Connection rejected: {err_map.get(err, err)}"))
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

"""协同测试：TCP 服务端/客户端，JSON 行协议。邀请码 5 分钟有效。"""
import json
import random
import socket
import string
import threading
import time

from PySide6.QtCore import QObject, Signal

PORT = 50505


class CollabServer(QObject):
    log_msg = Signal(str)
    nodes_changed = Signal()

    def __init__(self):
        super().__init__()
        self._sessions = {}   # id -> {sock, name, stats}
        self._lock = threading.Lock()
        self._code = None
        self._expiry = 0.0
        self._max_nodes = 0
        self._listen_sock = None
        self.active = False

    @property
    def invite_valid(self):
        return self._code and time.time() < self._expiry

    def generate_invite(self, max_nodes: int) -> str:
        self._code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        self._expiry = time.time() + 300
        self._max_nodes = max(1, max_nodes)
        if not self.active:
            self._start_listen()
        return self._code

    def _start_listen(self):
        # 优先 IPv6 双栈（同时接受 IPv4 与 IPv6），失败则回退纯 IPv4
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
        self.log_msg.emit(f"监听失败: {last_err}")

    def _accept_loop(self):
        while self.active:
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
                            self._sessions[sid] = {"sock": conn, "name": msg.get("name") or sid,
                                                   "stats": None}
                    self._send(conn, {"type": "joined" if ok else "refused"})
                    if ok:
                        self.log_msg.emit(f"节点 {msg.get('name') or sid} 已加入")
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

    def _send(self, sock, obj):
        try:
            sock.sendall((json.dumps(obj) + "\n").encode("utf-8"))
            return True
        except OSError:
            return False

    def broadcast(self, obj):
        with self._lock:
            socks = [v["sock"] for v in self._sessions.values()]
        for s in socks:
            self._send(s, obj)

    def get_nodes(self):
        with self._lock:
            return [(v["name"], dict(v["stats"]) if v["stats"] else None)
                    for v in self._sessions.values()]

    def shutdown(self):
        self.active = False
        if self._listen_sock:
            try:
                self._listen_sock.close()
            except OSError:
                pass
        with self._lock:
            sessions = list(self._sessions.values())
            self._sessions.clear()
        for v in sessions:
            try:
                v["sock"].close()
            except OSError:
                pass


class CollabClient(QObject):
    log_msg = Signal(str)
    status_msg = Signal(str)
    start_requested = Signal(dict)  # 主控下发的压测配置
    stop_requested = Signal()

    def __init__(self):
        super().__init__()
        self._sock = None
        self.connected = False

    def join(self, host: str, code: str, name: str):
        try:
            # 支持 "host" 或 "host:port" 格式（与主控页复制的地址一致）
            port = PORT
            if host.startswith("[") and "]" in host:  # IPv6 [::1]:50505
                inside, _, rest = host.partition("]")
                host = inside.strip("[")
                p = rest.lstrip(":")
                if p.isdigit() and 0 < int(p) < 65536:
                    port = int(p)
            elif host.count(":") == 1:  # IPv4:port
                h, _, p = host.rpartition(":")
                if p.isdigit() and 0 < int(p) < 65536:
                    host, port = h, int(p)
            s = socket.create_connection((host, port), timeout=8)
            s.sendall((json.dumps({"type": "join", "code": code.strip().upper(), "name": name}) + "\n").encode("utf-8"))
            s.settimeout(10)
            f = s.makefile("r", encoding="utf-8")
            line = f.readline()
            resp = json.loads(line) if line else {}
            if resp.get("type") != "joined":
                s.close()
                return False, "邀请码无效或已满员"
            self._sock = s
            self.connected = True
            threading.Thread(target=self._read_loop, args=(s, f), daemon=True).start()
            return True, "已加入"
        except OSError as e:
            return False, f"连接失败: {e}"

    def _read_loop(self, sock, f):
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
            self.status_msg.emit("与主控断开连接")
            try:
                sock.close()
            except OSError:
                pass

    def send_stats(self, stats: dict):
        if self._sock and self.connected:
            try:
                self._sock.sendall((json.dumps({"type": "stats", "stats": stats}) + "\n").encode("utf-8"))
            except OSError:
                pass

    def leave(self):
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

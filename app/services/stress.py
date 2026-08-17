"""压力测试引擎：多线程 worker + 令牌桶限速，支持 HTTP/HTTPS/TCP/UDP/ICMP。"""
import socket
import statistics
import threading
import time
from collections import deque

import requests
from PySide6.QtCore import QObject, Signal

from app.services.rate_limiter import TokenBucket

try:  # 抑制 HTTPS verify=False 产生的大量警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
except Exception:
    pass


def _percentile(data, p):
    if not data:
        return 0.0
    try:
        qs = statistics.quantiles(data, n=100)
        return qs[min(99, max(0, p - 1))]
    except Exception:
        return data[len(data) // 2]


# 错误码 -> 异常特征映射（引擎只存错误码，界面层负责按语言翻译）
_ERR_CODES = {
    "refused": "refused",
    "reset by peer": "reset",
    "unreachable": "unreachable",
    "timed out": "timeout",
    "getaddrinfo": "dns",
    "name or service not known": "dns",
    "handshake": "tls",
    "certificate": "cert",
    "closed": "closed",
    "no route to host": "unreachable",
    "network is down": "unreachable",
}


def _classify_conn_error(e) -> str:
    """把 requests 连接异常归类为稳定错误码。"""
    s = str(e).lower()
    for k, code in _ERR_CODES.items():
        if k in s:
            return code
    return "conn"


def _oserr_str(e) -> str:
    """把 socket OSError 归类为稳定错误码。"""
    s = str(e).lower()
    for k, code in _ERR_CODES.items():
        if k in s:
            return code
    eno = getattr(e, "errno", None)
    if eno:
        return f"errno_{eno}"
    return "conn"


def _http_req_bytes(r) -> int:
    """估算一次 HTTP 请求实际发送的字节数（请求行 + 头 + 体）。"""
    try:
        req = r.request
        n = len(req.method) + len(req.url) + 12  # "GET url HTTP/1.1\r\n\r\n"
        for k, v in (req.headers or {}).items():
            n += len(k) + len(str(v)) + 4        # "Key: Value\r\n"
        body = req.body
        if body:
            n += len(body)
        return n
    except Exception:
        return 0


class StressEngine(QObject):
    snapshot = Signal(dict)      # 周期性实时统计
    report_ready = Signal(dict)  # 结束后的汇总报告

    def __init__(self):
        super().__init__()
        self.running = False
        self._stop = threading.Event()
        self._reset()

    def _reset(self):
        self.total = 0
        self.success = 0
        self.fail = 0
        self.bytes_tx = 0           # 累计发送字节数
        self.latencies = []          # 采样延迟 ms
        self._recent = deque(maxlen=400)
        self._buckets = deque()      # [t, count] 100ms 桶
        self._lock = threading.Lock()
        self.config = None
        self._t0 = 0.0
        self._end = 0.0
        self._threads = []
        self.errors = {}             # 失败原因 -> 次数
        self.last_error = ""         # 最近一次失败原因

    def start(self, config: dict) -> bool:
        if self.running:
            return False
        self._reset()
        self.config = config
        self._stop.clear()
        self.running = True
        self._t0 = time.monotonic()
        self._end = self._t0 + config["duration"]
        bucket = TokenBucket(config["rate"])
        self._threads = []
        for _ in range(config["threads"]):
            t = threading.Thread(target=self._worker, args=(config, bucket), daemon=True)
            t.start()
            self._threads.append(t)
        threading.Thread(target=self._supervise, daemon=True).start()
        return True

    def stop(self):
        self._stop.set()

    # ---------- 内部 ----------

    def _worker(self, c, bucket):
        proto = c["protocol"]
        session = None
        if proto in ("HTTP", "HTTPS"):
            session = requests.Session()
            session.trust_env = False
        st = {"sock": None}
        payload = b"X" * max(1, c["packet_size"])
        timeout = c["timeout"] / 1000.0

        while not self._stop.is_set() and time.monotonic() < self._end:
            if not bucket.acquire(1.0):
                continue
            t1 = time.monotonic()
            ok = False
            err = None
            nbytes = 0  # 本次请求实际发送的字节数
            try:
                if proto == "HTTP":
                    r = session.get(c["url"], timeout=timeout, headers=c.get("headers"))
                    ok = r.status_code < 400
                    nbytes = _http_req_bytes(r)
                    if not ok:
                        err = f"HTTP {r.status_code}"
                elif proto == "HTTPS":
                    r = session.get(c["url"], timeout=timeout, headers=c.get("headers"), verify=False)
                    ok = r.status_code < 400
                    nbytes = _http_req_bytes(r)
                    if not ok:
                        err = f"HTTP {r.status_code}"
                elif proto == "TCP":
                    ok, err = self._tcp_once(c, payload, timeout, st)
                    nbytes = len(payload) if ok else 0
                elif proto == "UDP":
                    ok, err = self._udp_once(c, payload, timeout)
                    nbytes = len(payload) if ok else 0
                elif proto == "ICMP":
                    ok, err = self._icmp_once(c, timeout)
                    nbytes = 64 if ok else 0
            except requests.exceptions.Timeout:
                err = "timeout"
            except requests.exceptions.ConnectionError as e:
                err = _classify_conn_error(e)
            except Exception as e:
                err = type(e).__name__
            dt = (time.monotonic() - t1) * 1000.0
            with self._lock:
                self.total += 1
                self.bytes_tx += nbytes
                if ok:
                    self.success += 1
                else:
                    self.fail += 1
                    if err:
                        self.errors[err] = self.errors.get(err, 0) + 1
                        self.last_error = err
                self._recent.append(dt)
                if len(self.latencies) < 100000 and self.total % 5 == 0:
                    self.latencies.append(dt)
                now = time.monotonic()
                if self._buckets and now - self._buckets[-1][0] < 0.1:
                    self._buckets[-1][1] += 1
                else:
                    self._buckets.append([now, 1])
                    cutoff = now - 1.0
                    while self._buckets and self._buckets[0][0] < cutoff:
                        self._buckets.popleft()

        if session:
            session.close()
        if st["sock"]:
            try:
                st["sock"].close()
            except OSError:
                pass

    def _tcp_once(self, c, payload, timeout, st):
        try:
            if st["sock"] is None:
                st["sock"] = socket.create_connection((c["target"], c["port"]), timeout=timeout)
            st["sock"].sendall(payload)
            try:
                st["sock"].recv(1)
            except socket.timeout:
                pass
            return True, None
        except OSError as e:
            if st["sock"]:
                try:
                    st["sock"].close()
                except OSError:
                    pass
                st["sock"] = None
            return False, _oserr_str(e)

    def _udp_once(self, c, payload, timeout):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.settimeout(timeout)
                s.sendto(payload, (c["target"], c["port"]))
            return True, None
        except OSError as e:
            return False, _oserr_str(e)

    def _icmp_once(self, c, timeout):
        try:
            from icmplib import ping
            r = ping(c["target"], count=1, timeout=timeout, privileged=False)
            return r.is_alive, None if r.is_alive else "icmp_dead"
        except Exception as e:
            return False, type(e).__name__

    def _qps(self):
        with self._lock:
            if not self._buckets:
                return 0.0
            now = time.monotonic()
            cutoff = now - 1.0
            while self._buckets and self._buckets[0][0] < cutoff:
                self._buckets.popleft()
            return float(sum(b[1] for b in self._buckets))

    def _supervise(self):
        while True:
            alive = any(t.is_alive() for t in self._threads)
            left = self._end - time.monotonic()
            if self._stop.is_set() or (left <= 0 and not alive):
                break
            with self._lock:
                recent = list(self._recent)
                snap = {
                    "running": True,
                    "total": self.total,
                    "success": self.success,
                    "fail": self.fail,
                    "tx": self.bytes_tx,
                    "qps": self._qps_nolock(),
                    "avg": (sum(recent) / len(recent)) if recent else 0.0,
                    "active": sum(1 for t in self._threads if t.is_alive()),
                    "progress": min(1.0, (time.monotonic() - self._t0) / max(0.1, self.config["duration"])),
                    "last_error": self.last_error,
                }
            self.snapshot.emit(snap)
            time.sleep(0.5)
        # 结束：等 worker 退出（stop 已置位或超时）
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2.0)
        self.running = False
        with self._lock:
            lats = list(self.latencies)
            report = {
                "target": self.config["target"],
                "protocol": self.config["protocol"],
                "duration": time.monotonic() - self._t0,
                "total": self.total,
                "success": self.success,
                "fail": self.fail,
                "avg": (sum(lats) / len(lats)) if lats else 0.0,
                "p50": _percentile(lats, 50),
                "p90": _percentile(lats, 90),
                "p99": _percentile(lats, 99),
                "traffic_mb": self.total * (self.config["packet_size"] + 54) / 1024 / 1024,
                "bytes_tx": self.bytes_tx,
                "rate_limit": self.config["rate"],
                "errors": dict(self.errors),
            }
        self.report_ready.emit(report)

    def _qps_nolock(self):
        if not self._buckets:
            return 0.0
        now = time.monotonic()
        cutoff = now - 1.0
        while self._buckets and self._buckets[0][0] < cutoff:
            self._buckets.popleft()
        return float(sum(b[1] for b in self._buckets))


engine = StressEngine()

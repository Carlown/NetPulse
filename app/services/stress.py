"""压力测试引擎：多线程 worker + 令牌桶限速，支持 HTTP/HTTPS/TCP/UDP/ICMP，多目标并行。"""
import socket
import statistics
import threading
import time
from collections import deque

import requests
from PySide6.QtCore import QObject, QTimer, Signal

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
    ready = Signal()             # 所有 worker 线程已启动

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
        self._start_event = threading.Event()  # 线程同步启动屏障

    def start(self, config: dict) -> bool:
        """启动压测。线程创建在后台线程执行，ready 信号表示所有 worker 已就绪。"""
        if self.running:
            return False
        self._reset()
        self.config = config
        self._stop.clear()
        self.running = True
        threading.Thread(target=self._launch_workers, args=(config,), daemon=True).start()
        return True

    def _launch_workers(self, config):
        """在后台线程中创建并启动所有 worker，尽早开始发送快照让UI响应。"""
        bucket = TokenBucket(config["rate"])
        self._start_event.clear()
        self._threads = []
        # 先设置计时起点并启动监控线程，让UI立即收到快照反馈
        self._t0 = time.monotonic()
        self._end = self._t0 + config["duration"]
        threading.Thread(target=self._supervise, daemon=True).start()
        # 创建所有线程（它们会在 _start_event 处等待）
        for _ in range(config["threads"]):
            t = threading.Thread(target=self._worker, args=(config, bucket), daemon=True)
            t.start()
            self._threads.append(t)
        # 所有线程已创建完成，放行所有 worker 统一开始
        self._start_event.set()
        self.ready.emit()

    def stop(self):
        self._stop.set()
        self._start_event.set()  # 防止线程在等待启动事件时卡住

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

        # 等待所有线程就绪后统一开始（同步屏障）；等待期间也要响应停止信号，
        # 防止 stop() 先于 _launch_workers 的 clear() 执行时线程永久阻塞
        while not self._start_event.wait(timeout=0.2):
            if self._stop.is_set():
                if session:
                    session.close()
                return
        # 如果在等待期间收到了停止信号，直接退出
        if self._stop.is_set():
            if session:
                session.close()
            return

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
        poll_interval = 0.1  # 更频繁的检测间隔，UI更流畅、停止响应更快
        stop_deadline = None
        while True:
            alive = any(t.is_alive() for t in self._threads)
            left = self._end - time.monotonic()
            should_stop = self._stop.is_set() or left <= 0
            if should_stop and stop_deadline is None:
                # 刚进入停止阶段：设置总等待截止时间（1.5秒后放弃等待）
                stop_deadline = time.monotonic() + 1.5
            if should_stop:
                if not alive or (stop_deadline and time.monotonic() > stop_deadline):
                    break
                # 等待线程退出阶段：缩短轮询间隔，不再发快照
                time.sleep(0.05)
                continue
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
            time.sleep(poll_interval)
        # 结束：快速等待worker退出（daemon线程，1秒总超时足够）
        self._stop.set()
        deadline = time.monotonic() + 1.0
        for t in self._threads:
            remain = deadline - time.monotonic()
            if remain <= 0:
                break
            t.join(timeout=min(remain, 0.3))
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


class MultiStressEngine(QObject):
    """多目标管理器：每个目标一个独立 StressEngine，聚合实时统计与汇总报告。

    start() 接受 dict（单目标，兼容协同模式）或 list[dict]（多目标并行）。
    """

    snapshot = Signal(dict)      # 聚合实时统计（含分目标明细 targets）
    report_ready = Signal(dict)  # 聚合汇总报告（含分目标明细 targets）
    started = Signal()           # 所有 worker 线程已启动
    stopping = Signal()          # 收到停止信号，等待 worker 退出

    def __init__(self):
        super().__init__()
        self.running = False
        self._children = []
        self._snaps = {}
        self._reports = {}
        self._timer = QTimer(self)
        self._timer.setInterval(500)
        self._timer.timeout.connect(self._emit_aggregate)
        self._first_snap_emitted = False

    def start(self, configs) -> bool:
        if isinstance(configs, dict):
            configs = [configs]
        if self.running or not configs:
            return False
        self._children = []
        self._snaps = {}
        self._reports = {}
        self._first_snap_emitted = False
        self._ready_count = 0
        self._expected = len(configs)
        all_ok = False
        for i, c in enumerate(configs):
            e = StressEngine()
            e._idx = i
            e.snapshot.connect(lambda d, e=e: self._on_child_snap(e, d))
            e.report_ready.connect(lambda r, e=e: self._on_child_report(e, r))
            e.ready.connect(self._on_child_ready)
            # 先连接信号再启动，避免 ready 信号在 connect 前发出
            if e.start(c):
                self._children.append(e)
                all_ok = True
        if not all_ok:
            self.running = False
            return False
        self.running = True
        self._timer.start()
        # started 信号将在所有子引擎 ready 后通过 _on_child_ready 发出
        return True

    def _on_child_ready(self):
        """每个子引擎 worker 全部启动后调用；全部就绪时 emit started。"""
        self._ready_count += 1
        if self._ready_count >= len(self._children):
            self.started.emit()

    def stop(self):
        if not self.running:
            return
        self.stopping.emit()
        for e in self._children:
            e.stop()

    # ---------- 内部 ----------

    def _on_child_snap(self, child, d):
        self._snaps[child._idx] = (d, child.config or {})

    def _on_child_report(self, child, r):
        self._reports[child._idx] = r
        if len(self._reports) >= len(self._children):
            self._finish()

    def _emit_aggregate(self):
        if not self._snaps:
            return
        snaps = [self._snaps[i] for i in sorted(self._snaps)]
        targets = []
        last_err = ""
        for d, c in snaps:
            targets.append({
                "host": c.get("target", "?"),
                "total": d["total"], "success": d["success"], "fail": d["fail"],
                "qps": d.get("qps", 0.0), "avg": d.get("avg", 0.0),
                "tx": d.get("tx", 0),
            })
            if d.get("last_error"):
                last_err = d["last_error"]
        agg = {
            "running": True,
            "total": sum(t["total"] for t in targets),
            "success": sum(t["success"] for t in targets),
            "fail": sum(t["fail"] for t in targets),
            "tx": sum(t["tx"] for t in targets),
            "qps": sum(t["qps"] for t in targets),
            "avg": (sum(t["avg"] * max(1, t["total"]) for t in targets)
                    / sum(max(1, t["total"]) for t in targets)),
            "active": sum(d.get("active", 0) for d, _ in snaps),
            "progress": min(d.get("progress", 0.0) for d, _ in snaps),
            "last_error": last_err,
            "targets": targets,
        }
        self.snapshot.emit(agg)

    def _finish(self):
        self._timer.stop()
        rs = [self._reports[i] for i in sorted(self._reports)]
        self.running = False
        self._children = []
        self._snaps = {}

        total = sum(r["total"] for r in rs)
        tw = total or 1

        def wavg(key):
            return sum(r[key] * r["total"] for r in rs) / tw

        errors = {}
        for r in rs:
            for k, v in (r.get("errors") or {}).items():
                errors[k] = errors.get(k, 0) + v
        single = len(rs) == 1
        report = {
            "target": rs[0]["target"] if single else f"{len(rs)}",
            "protocol": rs[0]["protocol"] if single else "MIX",
            "duration": max(r["duration"] for r in rs),
            "total": total,
            "success": sum(r["success"] for r in rs),
            "fail": sum(r["fail"] for r in rs),
            "avg": wavg("avg"), "p50": wavg("p50"),
            "p90": wavg("p90"), "p99": wavg("p99"),
            "traffic_mb": sum(r.get("traffic_mb", 0.0) for r in rs),
            "bytes_tx": sum(r.get("bytes_tx", 0) for r in rs),
            "rate_limit": sum(r.get("rate_limit", 0) for r in rs),
            "errors": errors,
            "targets": [{
                "target": r["target"], "protocol": r["protocol"],
                "duration": r["duration"], "total": r["total"],
                "success": r["success"], "fail": r["fail"],
                "avg": r["avg"], "p50": r["p50"], "p90": r["p90"], "p99": r["p99"],
                "bytes_tx": r.get("bytes_tx", 0), "rate_limit": r.get("rate_limit", 0),
                "errors": r.get("errors") or {},
            } for r in rs],
        }
        self.report_ready.emit(report)


engine = MultiStressEngine()

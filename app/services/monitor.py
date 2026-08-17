"""系统监控服务：后台线程每秒采样 CPU/内存/网络，Qt 信号分发到 UI。"""
import threading
import time

import psutil
from PySide6.QtCore import QObject, Signal


class MonitorService(QObject):
    updated = Signal(dict)  # cpu, mem_percent, mem_used_gb, mem_total_gb, down_kbs, up_kbs, tcp_conns

    def __init__(self):
        super().__init__()
        self._stop = threading.Event()
        self._thread = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()

    def _loop(self):
        psutil.cpu_percent(None)  # 首次调用初始化
        last_net = psutil.net_io_counters()
        last_t = time.time()
        while not self._stop.is_set():
            try:
                cpu = psutil.cpu_percent(1.0)
                vm = psutil.virtual_memory()
                net = psutil.net_io_counters()
                now = time.time()
                dt = max(now - last_t, 1e-6)
                down = (net.bytes_recv - last_net.bytes_recv) / dt / 1024
                up = (net.bytes_sent - last_net.bytes_sent) / dt / 1024
                try:
                    tcp = len(psutil.net_connections(kind="tcp"))
                except Exception:
                    tcp = -1
                self.updated.emit({
                    "cpu": cpu,
                    "mem_percent": vm.percent,
                    "mem_used_gb": vm.used / 1024 ** 3,
                    "mem_total_gb": vm.total / 1024 ** 3,
                    "down_kbs": max(0.0, down),
                    "up_kbs": max(0.0, up),
                    "tcp_conns": tcp,
                })
                last_net, last_t = net, now
            except Exception:
                self._stop.wait(1.0)


monitor = MonitorService()

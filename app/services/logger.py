"""审计日志：文件落盘 + 内存缓冲（供导出）。"""
import logging
import os
import threading
import time
from collections import deque

from app.services.settings import settings


class AuditLog:
    def __init__(self):
        base = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "NetPulse", "logs")
        os.makedirs(base, exist_ok=True)
        self.file_path = os.path.join(base, time.strftime("%Y-%m-%d") + ".log")
        self.entries = deque(maxlen=5000)
        self._lock = threading.Lock()

        self._logger = logging.getLogger("NetPulse")
        self._logger.setLevel(logging.INFO)
        if not self._logger.handlers:
            fh = logging.FileHandler(self.file_path, encoding="utf-8")
            fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self._logger.addHandler(fh)

    def _log(self, level, msg):
        self._logger.log(level, msg)
        with self._lock:
            self.entries.append((time.strftime("%Y-%m-%d %H:%M:%S"),
                                 logging.getLevelName(level), msg))

    def info(self, msg):
        self._log(logging.INFO, msg)

    def warn(self, msg):
        self._log(logging.WARNING, msg)

    def warning(self, msg):
        """warn 的别名（兼容标准 logging 命名，避免调用方 AttributeError）。"""
        self._log(logging.WARNING, msg)

    def error(self, msg):
        self._log(logging.ERROR, msg)

    def export_text(self, path):
        """导出当前日期的完整磁盘日志，而不是仅导出本次进程的内存缓存。"""
        with self._lock:
            for handler in self._logger.handlers:
                try:
                    handler.flush()
                except Exception:
                    pass
            try:
                with open(self.file_path, "r", encoding="utf-8") as src:
                    data = src.read()
            except OSError:
                lines = [f"{t} [{lv}] {m}" for t, lv, m in list(self.entries)]
                data = "\n".join(lines)

        # 用户若恰好选择了当前日志文件本身，不要用写模式把源文件截断。
        if os.path.abspath(path) == os.path.abspath(self.file_path):
            return len(data.splitlines())
        with open(path, "w", encoding="utf-8") as f:
            f.write(data)
        return len(data.splitlines())


log = AuditLog()

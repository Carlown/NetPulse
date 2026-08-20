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
        with self._lock:
            lines = [f"{t} [{lv}] {m}" for t, lv, m in list(self.entries)]
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        return len(lines)


log = AuditLog()

"""令牌桶限速器：所有压测流量必须经过限速，保证速率上限可执行。"""
import threading
import time


class TokenBucket:
    def __init__(self, rate: float):
        self.rate = max(1.0, float(rate))       # tokens per second
        self.capacity = max(self.rate, 1.0)
        self.tokens = min(self.capacity, 1.0)
        self.last = time.monotonic()
        self._cond = threading.Condition()

    def _refill(self):
        now = time.monotonic()
        self.tokens = min(self.capacity, self.tokens + (now - self.last) * self.rate)
        self.last = now

    def acquire(self, timeout: float = 1.0) -> bool:
        """获取一个令牌；超时返回 False。"""
        deadline = time.monotonic() + timeout
        with self._cond:
            while True:
                self._refill()
                if self.tokens >= 1.0:
                    self.tokens -= 1.0
                    return True
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return False
                self._cond.wait(min(remaining, 0.2))

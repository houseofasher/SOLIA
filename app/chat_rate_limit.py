"""IP rate limit for public chat POST — prevents unauthenticated compute abuse."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict

from app.rate_limit import _env_int


class ChatRateLimiter:
    """Sliding-window limiter for POST /api/chat per client IP."""

    def __init__(self) -> None:
        self._max = _env_int("AUREON_CHAT_RATE_LIMIT_PER_MINUTE", 40)
        self._window_sec = 60.0
        self._lock = threading.Lock()
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def try_acquire(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_sec
        key = (client_ip or "unknown").strip()[:64]
        with self._lock:
            recent = [t for t in self._timestamps[key] if t >= cutoff]
            if len(recent) >= self._max:
                self._timestamps[key] = recent
                return False
            recent.append(now)
            self._timestamps[key] = recent
            return True


_limiter: ChatRateLimiter | None = None


def get_chat_rate_limiter() -> ChatRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = ChatRateLimiter()
    return _limiter

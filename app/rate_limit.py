"""In-memory IP rate limiter (nomad rate_limit_nerves pattern)."""

from __future__ import annotations

import os
import threading
import time
from collections import defaultdict


def _env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return max(1, int(raw))
    except ValueError:
        return default


class IpRateLimiter:
    """Sliding-window request counter per client IP."""

    def __init__(
        self,
        *,
        max_mutating_per_minute: int | None = None,
        window_sec: float = 60.0,
    ) -> None:
        self._max = max_mutating_per_minute or _env_int("AUREON_RATE_LIMIT_PER_MINUTE", 30)
        self._window_sec = window_sec
        self._lock = threading.Lock()
        self._timestamps: dict[str, list[float]] = defaultdict(list)

    def try_acquire(self, client_ip: str) -> bool:
        now = time.monotonic()
        cutoff = now - self._window_sec
        with self._lock:
            recent = [t for t in self._timestamps[client_ip] if t >= cutoff]
            if len(recent) >= self._max:
                self._timestamps[client_ip] = recent
                return False
            recent.append(now)
            self._timestamps[client_ip] = recent
            return True

    def snapshot(self) -> dict[str, int | float]:
        now = time.monotonic()
        cutoff = now - self._window_sec
        with self._lock:
            active_ips = sum(1 for ts in self._timestamps.values() if any(t >= cutoff for t in ts))
            total_recent = sum(len([t for t in ts if t >= cutoff]) for ts in self._timestamps.values())
        return {
            "max_mutating_per_minute": self._max,
            "window_sec": self._window_sec,
            "active_ips": active_ips,
            "requests_last_window": total_recent,
        }


_rate_limiter: IpRateLimiter | None = None


def get_rate_limiter() -> IpRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = IpRateLimiter()
    return _rate_limiter

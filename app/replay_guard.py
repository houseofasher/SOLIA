"""Replay protection for mutating requests (nomad replay_guard pattern)."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass


@dataclass
class ReplayGuardOptions:
    max_clock_skew_ms: int = 60_000
    nonce_ttl_ms: int = 120_000
    max_entries: int = 10_000


class ReplayGuard:
    def __init__(self, options: ReplayGuardOptions | None = None) -> None:
        self._options = options or ReplayGuardOptions()
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def validate(self, nonce: str, timestamp_ms: int, correlation_id: str) -> None:
        if not nonce or not nonce.strip():
            raise ValueError("Missing X-Nonce header.")
        self._purge()
        with self._lock:
            if len(self._seen) >= self._options.max_entries:
                oldest = next(iter(self._seen))
                del self._seen[oldest]
            now_ms = int(time.time() * 1000)
            if timestamp_ms <= 0 or abs(now_ms - timestamp_ms) > self._options.max_clock_skew_ms:
                raise ValueError("Message timestamp outside allowed clock skew window.")
            key = f"{correlation_id}:{nonce.strip()}"
            if key in self._seen:
                raise ValueError("Replay detected: duplicate nonce.")
            self._seen[key] = time.monotonic() + (self._options.nonce_ttl_ms / 1000.0)

    def _purge(self) -> None:
        now = time.monotonic()
        with self._lock:
            expired = [k for k, exp in self._seen.items() if exp <= now]
            for key in expired:
                del self._seen[key]


_replay_guard: ReplayGuard | None = None


def replay_guard_enabled() -> bool:
    return os.environ.get("AUREON_REPLAY_GUARD", "1").strip().lower() not in ("0", "false", "no")


def get_replay_guard() -> ReplayGuard:
    global _replay_guard
    if _replay_guard is None:
        _replay_guard = ReplayGuard()
    return _replay_guard

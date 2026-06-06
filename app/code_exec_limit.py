"""Global rate limit for subprocess code evaluation (DoS / abuse guard)."""

from __future__ import annotations

import os
import threading
import time
from collections import deque

_lock = threading.Lock()
_timestamps: deque[float] = deque()


def _max_per_minute() -> int:
    raw = os.environ.get("AUREON_CODE_EXEC_PER_MINUTE", "30").strip()
    try:
        return max(1, min(int(raw), 500))
    except ValueError:
        return 30


def try_acquire_code_exec() -> bool:
    """Return False when code subprocess budget for this minute is exhausted."""
    now = time.monotonic()
    cutoff = now - 60.0
    with _lock:
        while _timestamps and _timestamps[0] < cutoff:
            _timestamps.popleft()
        if len(_timestamps) >= _max_per_minute():
            return False
        _timestamps.append(now)
        return True

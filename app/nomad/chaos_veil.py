"""Chaos timing veil — nomad NOMAD_CHAOS_JITTER_MS pattern for response unpredictability."""

from __future__ import annotations

import os
import random
import time


def chaos_veil_enabled() -> bool:
    raw = os.environ.get("AUREON_CHAOS_VEIL", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def chaos_jitter_ms() -> int:
    raw = os.environ.get("AUREON_CHAOS_JITTER_MS", "40").strip()
    try:
        return max(0, min(200, int(raw)))
    except ValueError:
        return 40


def apply_chaos_veil() -> None:
    """Add random delay before sensitive responses — defeats trivial traffic analysis."""
    if not chaos_veil_enabled():
        return
    ceiling = chaos_jitter_ms()
    if ceiling <= 0:
        return
    time.sleep(random.randint(0, ceiling) / 1000.0)

"""Supply chain integrity — hash lock on requirements.txt (nomad supply_spleen pattern)."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

_EXPECTED_HASH: str | None = None
_VERIFIED = False


def requirements_path() -> Path:
    custom = os.environ.get("AUREON_REQUIREMENTS_PATH", "").strip()
    if custom:
        return Path(custom)
    return Path(__file__).resolve().parents[2] / "requirements.txt"


def compute_requirements_hash() -> str | None:
    path = requirements_path()
    if not path.is_file():
        return None
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest


def verify_supply_chain() -> dict[str, str | bool]:
    """Verify dependency manifest hash; optional pin via AUREON_REQUIREMENTS_SHA256."""
    global _VERIFIED
    actual = compute_requirements_hash()
    if actual is None:
        return {"ok": False, "detail": f"requirements manifest missing at {requirements_path()}"}

    expected = os.environ.get("AUREON_REQUIREMENTS_SHA256", "").strip().lower()
    if expected and actual.lower() != expected:
        return {
            "ok": False,
            "detail": f"requirements hash mismatch (expected {expected[:16]}…, got {actual[:16]}…)",
        }

    _VERIFIED = True
    detail = f"requirements.txt sha256={actual[:16]}…"
    if expected:
        detail += " (pinned)"
    return {"ok": True, "detail": detail, "hash": actual}


def supply_verified() -> bool:
    return _VERIFIED

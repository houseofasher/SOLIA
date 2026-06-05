"""Client allowlist — nomad NOMAD_CLIENT_ALLOWLIST pattern (API key hashes)."""

from __future__ import annotations

import hashlib
import hmac
import os


def allowlist_enabled() -> bool:
    return bool(os.environ.get("AUREON_CLIENT_ALLOWLIST", "").strip())


def _allowed_entries() -> set[str]:
    raw = os.environ.get("AUREON_CLIENT_ALLOWLIST", "").strip()
    if not raw:
        return set()
    return {entry.strip().lower() for entry in raw.split(",") if entry.strip()}


def is_client_allowed(api_key: str) -> bool:
    """Return True if allowlist disabled or key matches an entry (raw or sha256 hex)."""
    entries = _allowed_entries()
    if not entries:
        return True
    key = api_key.strip()
    if not key:
        return False
    key_lower = key.lower()
    if key_lower in entries:
        return True
    key_hash = hashlib.sha256(key.encode("utf-8")).hexdigest().lower()
    return key_hash in entries


def verify_client_allowlist(api_key: str | None) -> None:
    if not allowlist_enabled():
        return
    if not api_key or not is_client_allowed(api_key):
        raise ValueError("Client not on allowlist (AUREON_CLIENT_ALLOWLIST)")

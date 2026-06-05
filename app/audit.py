"""Tamper-evident HMAC-chained audit log (nomad audit_immune pattern)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)

AuditEventType = Literal[
    "auth_failed",
    "auth_succeeded",
    "rate_limit_exceeded",
    "replay_detected",
    "organism_lockdown",
    "organism_pulse",
    "mutating_request",
    "training_started",
    "training_completed",
]

AuditEvent = dict[str, Any]


class AuditLog:
    """Append-only JSONL log with HMAC-chained entries."""

    def __init__(self, log_dir: str | None = None, chain_key_hex: str | None = None) -> None:
        key_hex = (chain_key_hex or os.environ.get("AUREON_AUDIT_CHAIN_KEY", "")).strip()
        if key_hex:
            self._chain_key = bytes.fromhex(key_hex)
        else:
            self._chain_key = secrets.token_bytes(32)
            logger.warning(
                "AUREON_AUDIT_CHAIN_KEY not set — audit chain uses ephemeral key (not durable across restarts)."
            )
        log_root = log_dir or os.environ.get("AUREON_AUDIT_LOG_DIR", "data/audit")
        self._file_path = Path(log_root) / "aureon-audit.jsonl"
        self._entries: list[AuditEvent] = []
        if self._file_path.parent:
            self._file_path.parent.mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    def _load_from_disk(self) -> None:
        if not self._file_path.is_file():
            return
        for line in self._file_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                self._entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    def _sign_entry(self, event: dict[str, Any]) -> str:
        prev_id = event.get("prev_entry_id") or "GENESIS"
        payload = "|".join(
            [
                str(event.get("id", "")),
                str(event.get("ts", "")),
                str(event.get("type", "")),
                prev_id,
                str(event.get("detail") or ""),
                str(event.get("correlation_id") or ""),
            ]
        )
        return hmac.new(self._chain_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def record(
        self,
        event_type: AuditEventType,
        *,
        correlation_id: str | None = None,
        peer: str | None = None,
        detail: str | None = None,
    ) -> AuditEvent:
        prev = self._entries[-1] if self._entries else None
        base: dict[str, Any] = {
            "id": f"{int(time.time() * 1000)}-{secrets.token_hex(8)}",
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "type": event_type,
            "prev_entry_id": prev["id"] if prev else "",
            "correlation_id": correlation_id,
            "peer": peer,
            "detail": detail,
        }
        base["entry_mac"] = self._sign_entry(base)
        self._entries.append(base)
        with self._file_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(base, separators=(",", ":")) + "\n")
        return base

    def verify_chain(self) -> dict[str, Any]:
        errors: list[str] = []
        prev_id = ""
        for entry in self._entries:
            stored_mac = entry.get("entry_mac", "")
            expected = self._sign_entry(entry)
            if stored_mac != expected:
                errors.append(f"Entry {entry.get('id')}: HMAC mismatch (tamper detected)")
            if entry.get("prev_entry_id", "") != prev_id:
                errors.append(
                    f"Entry {entry.get('id')}: chain broken (expected prev {prev_id!r}, "
                    f"got {entry.get('prev_entry_id')!r})"
                )
            prev_id = str(entry.get("id", ""))
        return {"valid": not errors, "errors": errors, "length": len(self._entries)}

    def query(self, limit: int = 100) -> list[AuditEvent]:
        return self._entries[-limit:]

    def head_id(self) -> str:
        return str(self._entries[-1]["id"]) if self._entries else "genesis"


_audit_log: AuditLog | None = None


def get_audit_log() -> AuditLog:
    global _audit_log
    if _audit_log is None:
        _audit_log = AuditLog()
    return _audit_log

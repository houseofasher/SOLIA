"""Organism vitals and lockdown guard (nomad sovereign_organism pattern, Aureon-adapted)."""

from __future__ import annotations

import hashlib
import logging
import os
import threading
from typing import Any, Literal

from sqlalchemy import text

from app.audit import get_audit_log
from app.rate_limit import get_rate_limiter
from app.security import api_key_required

logger = logging.getLogger(__name__)

OrganState = Literal["vital", "dormant", "critical"]


def _is_production() -> bool:
    return os.environ.get("RAILWAY_ENVIRONMENT", "").strip() != "" or os.environ.get(
        "AUREON_ENV", ""
    ).strip().lower() in ("production", "prod")


class AureonOrganism:
    """
    Simplified security organism — checks auth, audit chain, rate limits, and DB.
    Partial compromise triggers lockdown on mutating operations.
    """

    DOCTRINE = (
        "All security organs must be healthy simultaneously. "
        "Audit tamper or critical organ failure blocks mutating operations."
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pulse_generation = 0
        self._lockdown_reason: str | None = None
        self._organs: dict[str, dict[str, Any]] = {}

    def pulse(self) -> None:
        with self._lock:
            self._pulse_generation += 1
            self._organs = {
                "auth_gateway": self._check_auth_gateway(),
                "audit_immune": self._check_audit_immune(),
                "rate_limit_nerves": self._check_rate_limit_nerves(),
                "database_marrow": self._check_database(),
            }
            critical = [oid for oid, o in self._organs.items() if o["state"] == "critical"]
            non_auth_critical = [oid for oid in critical if oid != "auth_gateway"]
            if non_auth_critical:
                self._lockdown_reason = f"critical organs: {', '.join(non_auth_critical)}"
            else:
                self._lockdown_reason = None

        get_audit_log().record(
            "organism_pulse",
            detail=f"pulse gen={self._pulse_generation} vital={self.is_vital()}",
        )

    def is_vital(self) -> bool:
        if self._lockdown_reason:
            return False
        return all(o["state"] in ("vital", "dormant") for o in self._organs.values()) if self._organs else True

    def is_learning_allowed(self) -> bool:
        """
        Background auto-learn may run when storage/audit organs are healthy.

        Missing API key makes auth_gateway critical for mutating HTTP routes but must
        not block unattended learning on Railway.
        """
        if self._lockdown_reason:
            return False
        if not self._organs:
            return True
        for organ_id, organ in self._organs.items():
            if organ_id == "auth_gateway":
                continue
            if organ["state"] == "critical":
                return False
        return True

    def require_vital(self, operation: str) -> None:
        if not self.is_vital():
            reason = self._lockdown_reason or "organ not vital"
            raise OrganismLockdownError(
                f"ORGANISM_LOCKDOWN: {operation} blocked — {reason}. {self.DOCTRINE}"
            )

    def enter_lockdown(self, reason: str) -> None:
        with self._lock:
            self._lockdown_reason = reason
        logger.error("Organism lockdown: %s", reason)
        get_audit_log().record("organism_lockdown", detail=reason)

    def get_fingerprint(self) -> str:
        audit_head = get_audit_log().head_id()
        pulse = str(self._pulse_generation)
        rate = str(get_rate_limiter().snapshot().get("requests_last_window", 0))
        payload = f"{audit_head}|{pulse}|{rate}|{self._lockdown_reason or 'ok'}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get_vitals_report(self) -> dict[str, Any]:
        if not self._organs:
            self.pulse()
        return {
            "vital": self.is_vital(),
            "learning_allowed": self.is_learning_allowed(),
            "pulse_generation": self._pulse_generation,
            "organism_fingerprint": self.get_fingerprint(),
            "lockdown_reason": self._lockdown_reason,
            "organs": [
                {
                    "id": oid,
                    "name": o["name"],
                    "state": o["state"],
                    "role": o["role"],
                    "detail": o.get("detail"),
                }
                for oid, o in self._organs.items()
            ],
            "doctrine": self.DOCTRINE,
        }

    def _check_auth_gateway(self) -> dict[str, Any]:
        if api_key_required():
            return {
                "name": "Auth Gateway",
                "role": "API key perimeter",
                "state": "vital",
                "detail": "AUREON_API_KEY configured",
            }
        if _is_production():
            return {
                "name": "Auth Gateway",
                "role": "API key perimeter",
                "state": "critical",
                "detail": "AUREON_API_KEY required in production",
            }
        return {
            "name": "Auth Gateway",
            "role": "API key perimeter",
            "state": "dormant",
            "detail": "Dev mode — mutating endpoints unauthenticated",
        }

    def _check_audit_immune(self) -> dict[str, Any]:
        chain = get_audit_log().verify_chain()
        if chain["valid"]:
            return {
                "name": "Audit Immune System",
                "role": "Tamper-evident audit chain",
                "state": "vital",
                "detail": f"chain intact ({chain['length']} entries)",
            }
        audit_key_set = bool(os.environ.get("AUREON_AUDIT_CHAIN_KEY", "").strip())
        if not audit_key_set:
            return {
                "name": "Audit Immune System",
                "role": "Tamper-evident audit chain",
                "state": "dormant",
                "detail": "Dev mode — ephemeral audit key (set AUREON_AUDIT_CHAIN_KEY in production)",
            }
        return {
            "name": "Audit Immune System",
            "role": "Tamper-evident audit chain",
            "state": "critical",
            "detail": "; ".join(chain["errors"][:3]),
        }

    def _check_rate_limit_nerves(self) -> dict[str, Any]:
        snap = get_rate_limiter().snapshot()
        return {
            "name": "Rate Limit Nerves",
            "role": "Per-IP sliding window",
            "state": "vital",
            "detail": f"limit {snap['max_mutating_per_minute']}/min, active_ips={snap['active_ips']}",
        }

    def _check_database(self) -> dict[str, Any]:
        try:
            from db.session import get_engine

            with get_engine().connect() as conn:
                conn.execute(text("SELECT 1"))
            url = os.environ.get("DATABASE_URL", "")
            if url.startswith("postgresql"):
                detail = "PostgreSQL reachable"
            elif url:
                detail = "Database reachable"
            else:
                detail = "SQLite local fallback"
            return {
                "name": "Database Marrow",
                "role": "Persistent brain storage",
                "state": "vital",
                "detail": detail,
            }
        except Exception as exc:
            return {
                "name": "Database Marrow",
                "role": "Persistent brain storage",
                "state": "critical",
                "detail": str(exc)[:200],
            }


class OrganismLockdownError(Exception):
    pass


_organism: AureonOrganism | None = None


def get_organism() -> AureonOrganism:
    global _organism
    if _organism is None:
        _organism = AureonOrganism()
    return _organism

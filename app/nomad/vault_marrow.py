"""Vault marrow — secrets bound to organism fingerprint (nomad vault_marrow pattern)."""

from __future__ import annotations

import json
import os
from pathlib import Path


def secrets_file_path() -> Path | None:
    from app.railway_env import get_railway_bootstrap_report

    report = get_railway_bootstrap_report()
    path = report.get("secrets_file")
    if path:
        candidate = Path(str(path))
        if candidate.is_file():
            return candidate
    data_dir = os.environ.get("AUREON_DATA_DIR", "data").strip() or "data"
    candidate = Path(data_dir) / "railway-secrets.json"
    return candidate if candidate.is_file() else None


def vault_binding_enabled() -> bool:
    return os.environ.get("AUREON_VAULT_BIND_FINGERPRINT", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )


def check_vault_marrow(organism_fingerprint: str) -> dict[str, str | bool]:
    path = secrets_file_path()
    if not path:
        if vault_binding_enabled():
            return {"ok": False, "detail": "Vault binding enabled but secrets file missing"}
        return {"ok": True, "detail": "No persisted secrets vault (optional)"}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "detail": f"Secrets vault unreadable: {exc}"}

    if not isinstance(payload, dict):
        return {"ok": False, "detail": "Secrets vault invalid format"}

    if vault_binding_enabled():
        bound = str(payload.get("organism_fingerprint", "")).strip()
        if bound and bound != organism_fingerprint:
            return {
                "ok": False,
                "detail": "Secrets vault fingerprint mismatch — possible tamper or redeploy",
            }

    keys = [k for k in payload if k.startswith("AUREON_")]
    return {"ok": True, "detail": f"Vault marrow sealed ({len(keys)} secrets at {path.name})"}

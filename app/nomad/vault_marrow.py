"""Vault marrow — secrets bound to organism fingerprint (nomad vault_marrow pattern)."""

from __future__ import annotations

import hashlib
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


def vault_binding_fingerprint() -> str:
    """
    Stable vault seal — must NOT change every organism pulse.

    The operational organism fingerprint includes audit head and pulse count;
    using that for vault binding causes false critical states during learning.
    """
    from app.nomad.supply_spleen import verify_supply_chain

    data_dir = os.environ.get("AUREON_DATA_DIR", "data").strip() or "data"
    has_api_key = "1" if os.environ.get("AUREON_API_KEY", "").strip() else "0"
    has_audit_key = "1" if os.environ.get("AUREON_AUDIT_CHAIN_KEY", "").strip() else "0"
    supply = verify_supply_chain().get("hash", "no-supply") or "no-supply"
    payload = f"aureon-vault-v1|{data_dir}|{supply}|{has_api_key}|{has_audit_key}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _env_secrets_configured() -> bool:
    return bool(os.environ.get("AUREON_API_KEY", "").strip())


def _ensure_secrets_file_from_env() -> Path | None:
    if not _env_secrets_configured():
        return None
    from app.railway_env import sync_env_secrets_to_file

    return sync_env_secrets_to_file()


def seal_vault_fingerprint(path: Path | None = None) -> Path | None:
    """Write stable vault binding fingerprint into the secrets file."""
    target = path or secrets_file_path()
    if not target:
        target = _ensure_secrets_file_from_env()
    if not target or not target.is_file():
        return None
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload["organism_fingerprint"] = vault_binding_fingerprint()
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def check_vault_marrow(_organism_fingerprint: str | None = None) -> dict[str, str | bool]:
    """Validate secrets vault. Operational fingerprint arg is ignored (stable bind used)."""
    _ = _organism_fingerprint
    binding_fp = vault_binding_fingerprint()
    path = secrets_file_path()
    if not path:
        if _env_secrets_configured():
            path = _ensure_secrets_file_from_env()
        if not path:
            if vault_binding_enabled() and not _env_secrets_configured():
                return {"ok": False, "detail": "Vault binding enabled but secrets file missing"}
            if _env_secrets_configured():
                return {"ok": True, "detail": "Secrets in Railway env (vault file pending sync)"}
            return {"ok": True, "detail": "No persisted secrets vault (optional)"}

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return {"ok": False, "detail": f"Secrets vault unreadable: {exc}"}

    if not isinstance(payload, dict):
        return {"ok": False, "detail": "Secrets vault invalid format"}

    if vault_binding_enabled():
        bound = str(payload.get("organism_fingerprint", "")).strip()
        if not bound or bound != binding_fp:
            sealed = seal_vault_fingerprint(path)
            if not sealed:
                return {"ok": False, "detail": "Could not seal vault fingerprint"}
            if bound and bound != binding_fp:
                return {"ok": True, "detail": f"Vault marrow re-sealed ({path.name})"}
            return {"ok": True, "detail": f"Vault marrow sealed ({path.name})"}

    keys = [k for k in payload if k.startswith("AUREON_")]
    return {"ok": True, "detail": f"Vault marrow sealed ({len(keys)} secrets at {path.name})"}

"""Vault marrow tests."""

from __future__ import annotations

import json

from app.nomad.vault_marrow import (
    check_vault_marrow,
    seal_vault_fingerprint,
    vault_binding_fingerprint,
)


def test_vault_binding_fingerprint_is_stable(monkeypatch):
    monkeypatch.setenv("AUREON_DATA_DIR", "/data")
    monkeypatch.setenv("AUREON_API_KEY", "key-a")
    monkeypatch.setenv("AUREON_AUDIT_CHAIN_KEY", "audit-a")
    first = vault_binding_fingerprint()
    second = vault_binding_fingerprint()
    assert first == second


def test_vault_ok_when_env_keys_sync_to_file(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_API_KEY", "test-key-from-railway-vars")
    monkeypatch.setenv("AUREON_AUDIT_CHAIN_KEY", "abc123")
    monkeypatch.setenv("AUREON_VAULT_BIND_FINGERPRINT", "1")

    from app.railway_env import bootstrap_railway_environment

    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    bootstrap_railway_environment()

    result = check_vault_marrow()
    assert result["ok"] is True

    secrets = json.loads((tmp_path / "railway-secrets.json").read_text(encoding="utf-8"))
    assert secrets["AUREON_API_KEY"] == "test-key-from-railway-vars"
    assert secrets["organism_fingerprint"] == vault_binding_fingerprint()


def test_vault_reseals_on_fingerprint_mismatch(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_API_KEY", "k")
    monkeypatch.setenv("AUREON_VAULT_BIND_FINGERPRINT", "1")

    secrets_path = tmp_path / "railway-secrets.json"
    secrets_path.write_text(
        json.dumps({"AUREON_API_KEY": "k", "organism_fingerprint": "stale-fingerprint"}),
        encoding="utf-8",
    )

    from app.railway_env import _bootstrap_report

    _bootstrap_report.clear()
    _bootstrap_report.update({"secrets_file": str(secrets_path)})

    result = check_vault_marrow()
    assert result["ok"] is True
    payload = json.loads(secrets_path.read_text(encoding="utf-8"))
    assert payload["organism_fingerprint"] == vault_binding_fingerprint()


def test_seal_vault_fingerprint(tmp_path, monkeypatch):
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("AUREON_API_KEY", "k")
    path = tmp_path / "railway-secrets.json"
    path.write_text(json.dumps({"AUREON_API_KEY": "k"}), encoding="utf-8")
    seal_vault_fingerprint(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["organism_fingerprint"] == vault_binding_fingerprint()

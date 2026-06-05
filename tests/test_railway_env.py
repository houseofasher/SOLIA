"""Railway environment auto-bootstrap tests."""

from __future__ import annotations

import json
import os

import pytest

from app import railway_env


@pytest.fixture(autouse=True)
def _reset_bootstrap_report():
    railway_env._bootstrap_report = {}
    yield
    railway_env._bootstrap_report = {}


def test_bootstrap_skips_locally(tmp_path, monkeypatch):
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("PORT", raising=False)
    report = railway_env.bootstrap_railway_environment()
    assert report["railway"] is False
    assert "AUREON_API_KEY" not in os.environ or os.environ.get("AUREON_API_KEY") == ""


def test_bootstrap_provisions_secrets_on_railway(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("AUREON_API_KEY", raising=False)
    monkeypatch.delenv("AUREON_AUDIT_CHAIN_KEY", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))

    report = railway_env.bootstrap_railway_environment()

    assert report["api_key"] == "generated"
    assert report["audit_chain_key"] == "generated"
    assert report["database"] == "sqlite"
    assert os.environ["AUREON_API_KEY"]
    assert len(os.environ["AUREON_AUDIT_CHAIN_KEY"]) == 64
    assert os.environ["DATABASE_URL"].startswith("sqlite:///")

    secrets_file = tmp_path / "railway-secrets.json"
    assert secrets_file.is_file()
    payload = json.loads(secrets_file.read_text(encoding="utf-8"))
    assert payload["AUREON_API_KEY"] == os.environ["AUREON_API_KEY"]


def test_bootstrap_restores_persisted_secrets(tmp_path, monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.delenv("AUREON_API_KEY", raising=False)
    monkeypatch.delenv("AUREON_AUDIT_CHAIN_KEY", raising=False)
    monkeypatch.setenv("AUREON_DATA_DIR", str(tmp_path))
    (tmp_path / "railway-secrets.json").write_text(
        json.dumps(
            {
                "AUREON_API_KEY": "persisted-api-key",
                "AUREON_AUDIT_CHAIN_KEY": "a" * 64,
            }
        ),
        encoding="utf-8",
    )

    report = railway_env.bootstrap_railway_environment()

    assert report["api_key"] == "restored"
    assert report["audit_chain_key"] == "restored"
    assert os.environ["AUREON_API_KEY"] == "persisted-api-key"


def test_bootstrap_uses_postgres_when_linked(monkeypatch):
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@host:5432/db")
    monkeypatch.setenv("AUREON_API_KEY", "already-set")
    monkeypatch.setenv("AUREON_AUDIT_CHAIN_KEY", "b" * 64)

    report = railway_env.bootstrap_railway_environment()

    assert report["database"] == "postgresql"
    assert report["database_source"] == "env"
    assert report["api_key"] == "env"

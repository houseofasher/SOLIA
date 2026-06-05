"""Nomad-inspired organism, audit, rate limit, and replay guard tests."""

from __future__ import annotations

import json
import secrets
import time

import pytest
from fastapi.testclient import TestClient

from app.audit import AuditLog
from app.main import app
from app.organism import AureonOrganism
from app.rate_limit import IpRateLimiter
from app.replay_guard import ReplayGuard, ReplayGuardOptions


client = TestClient(app)


def auth_headers(key: str = "test-secret-key") -> dict[str, str]:
    return {
        "X-API-Key": key,
        "X-Timestamp": str(int(time.time() * 1000)),
        "X-Nonce": secrets.token_hex(16),
        "X-Correlation-ID": f"test-{secrets.token_hex(8)}",
    }


def test_audit_chain_integrity(tmp_path):
    log = AuditLog(log_dir=str(tmp_path), chain_key_hex=secrets.token_hex(32))
    log.record("auth_succeeded", detail="test")
    log.record("mutating_request", detail="POST /api/test")
    chain = log.verify_chain()
    assert chain["valid"] is True
    assert chain["length"] == 2


def test_audit_chain_detects_tamper(tmp_path):
    log = AuditLog(log_dir=str(tmp_path), chain_key_hex=secrets.token_hex(32))
    log.record("auth_succeeded", detail="ok")
    log_path = tmp_path / "aureon-audit.jsonl"
    line = json.loads(log_path.read_text(encoding="utf-8").strip())
    line["detail"] = "tampered"
    log_path.write_text(json.dumps(line) + "\n", encoding="utf-8")
    log2 = AuditLog(log_dir=str(tmp_path), chain_key_hex=log._chain_key.hex())  # noqa: SLF001
    result = log2.verify_chain()
    assert result["valid"] is False
    assert any("HMAC mismatch" in e for e in result["errors"])


def test_replay_guard_rejects_duplicate_nonce():
    guard = ReplayGuard(ReplayGuardOptions(max_clock_skew_ms=60_000))
    ts = int(time.time() * 1000)
    guard.validate("nonce-1", ts, "corr-a")
    with pytest.raises(ValueError, match="Replay detected"):
        guard.validate("nonce-1", ts, "corr-a")


def test_replay_guard_rejects_stale_timestamp():
    guard = ReplayGuard()
    stale = int(time.time() * 1000) - 120_000
    with pytest.raises(ValueError, match="clock skew"):
        guard.validate("nonce-x", stale, "corr-b")


def test_rate_limiter_blocks_burst():
    limiter = IpRateLimiter(max_mutating_per_minute=2)
    assert limiter.try_acquire("1.2.3.4") is True
    assert limiter.try_acquire("1.2.3.4") is True
    assert limiter.try_acquire("1.2.3.4") is False


def test_organism_vitals_endpoint():
    response = client.get("/organism/vitals")
    assert response.status_code == 200
    body = response.json()
    assert "vital" in body
    assert "organs" in body
    assert "organism_fingerprint" in body
    assert len(body["organs"]) >= 4


def test_mutating_requires_replay_headers_when_api_key_set(monkeypatch):
    monkeypatch.setenv("AUREON_API_KEY", "test-secret-key")
    response = client.post("/api/brain/bootstrap")
    assert response.status_code == 400
    response = client.post("/api/brain/bootstrap", headers=auth_headers())
    assert response.status_code == 200


def test_mutating_rejects_bad_api_key_with_replay(monkeypatch):
    monkeypatch.setenv("AUREON_API_KEY", "test-secret-key")
    headers = auth_headers(key="wrong-key")
    response = client.post("/api/brain/bootstrap", headers=headers)
    assert response.status_code == 401


def test_correlation_id_echoed():
    response = client.get("/health", headers={"X-Correlation-ID": "my-trace-123"})
    assert response.headers.get("X-Correlation-ID") == "my-trace-123"


def test_organism_lockdown_on_critical_auth(monkeypatch):
    monkeypatch.setenv("AUREON_API_KEY", "")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    org = AureonOrganism()
    org.pulse()
    assert org.is_vital() is False
    assert org.is_learning_allowed() is True
    with pytest.raises(Exception, match="ORGANISM_LOCKDOWN"):
        org.require_vital("test op")

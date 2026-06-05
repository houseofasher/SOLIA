"""Security regression tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fastapi import HTTPException

from app.main import app
from app.security import (
    clamp_subdomain_limit,
    is_safe_webhook_url,
    load_json_file_bounded,
    resolve_path_under,
    validate_model_payload,
    validate_slug,
)


client = TestClient(app)


def test_slug_validation_rejects_injection():
    with pytest.raises(HTTPException):
        validate_slug("../etc/passwd")
    with pytest.raises(HTTPException):
        validate_slug("DROP TABLE")
    assert validate_slug("computer_science") == "computer_science"


def test_subdomain_limit_capped():
    assert clamp_subdomain_limit(9999) == 20


def test_webhook_blocks_internal_ssrf():
    assert is_safe_webhook_url("http://127.0.0.1/hook") is False
    assert is_safe_webhook_url("http://169.254.169.254/") is False
    assert is_safe_webhook_url("file:///etc/passwd") is False
    assert is_safe_webhook_url("https://hooks.example.com/alert") is True


def test_path_traversal_blocked():
    base = Path(tempfile.mkdtemp())
    with pytest.raises(ValueError):
        resolve_path_under(base, Path("../../etc/passwd"))


def test_json_size_limit():
    path = Path(tempfile.mktemp(suffix=".json"))
    path.write_text("{" + "x" * 100 + "}", encoding="utf-8")
    with pytest.raises(ValueError):
        load_json_file_bounded(path, max_bytes=10)


def test_model_payload_bounds():
    validate_model_payload(
        {
            "layer_sizes": [4, 2],
            "weights": [[[0.0] * 4] * 2],
            "biases": [[0.0] * 2],
        }
    )
    with pytest.raises(ValueError):
        validate_model_payload({"layer_sizes": [99999], "weights": [], "biases": []})


def test_mutating_endpoints_require_api_key_when_set(monkeypatch):
    monkeypatch.setenv("AUREON_API_KEY", "test-secret-key")
    response = client.post("/api/brain/bootstrap")
    assert response.status_code == 401
    response = client.post("/api/brain/bootstrap", headers={"X-API-Key": "test-secret-key"})
    assert response.status_code == 200


def test_health_is_public():
    assert client.get("/health").status_code == 200


def test_invalid_domain_slug_rejected():
    response = client.post("/api/brain/domain/not-valid!")
    assert response.status_code == 400


def test_security_headers_present():
    response = client.get("/health")
    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"

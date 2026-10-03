"""Phase 9 hardening tests: readiness, security headers, non-leaking errors,
and the prod config fail-fast guards (PHASE_9 tasks 1-3)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import app.main as main_module
from app.core.config import Settings
from app.main import app

client = TestClient(app)


# --- readiness / liveness ---------------------------------------------------

def test_health_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_readiness_up() -> None:
    # SQLite creates the file on connect, so SELECT 1 succeeds even on a fresh
    # checkout -> the happy path is deterministic in CI.
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ready", "db": "up"}


def test_readiness_down_returns_503(monkeypatch) -> None:
    class _Boom:
        def connect(self):  # emulate an unreachable DB
            raise RuntimeError("db down")

    monkeypatch.setattr(main_module, "engine", _Boom())
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    assert resp.json() == {"status": "unavailable", "db": "down"}


# --- security headers -------------------------------------------------------

def test_security_headers_present() -> None:
    resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
    assert resp.headers["Cache-Control"] == "no-store"
    assert "Permissions-Policy" in resp.headers


# --- error envelope: never leak internals -----------------------------------

def test_unhandled_error_does_not_leak() -> None:
    secret = "DB_PASSWORD=super-secret-value"

    @app.get("/_boom-for-test")
    def _boom():
        raise RuntimeError(secret)

    try:
        err_client = TestClient(app, raise_server_exceptions=False)
        resp = err_client.get("/_boom-for-test")
        assert resp.status_code == 500
        body = resp.json()
        # Generic, traceable envelope ...
        assert body["error"]["status_code"] == 500
        assert body["error"]["message"] == "Internal server error"
        assert body["error"]["request_id"]
        # ... and the real exception text never reaches the client.
        assert secret not in resp.text
    finally:
        app.router.routes = [
            r for r in app.router.routes
            if getattr(r, "path", None) != "/_boom-for-test"
        ]


def test_validation_error_returns_envelope_without_raw_values() -> None:
    # Missing required `student_id` -> RequestValidationError handler.
    resp = client.post("/recommend", json={"top_k": 999999})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["message"] == "Invalid request"
    fields = {d["field"] for d in body["error"]["details"]}
    assert "student_id" in fields
    # The offending value is never echoed back.
    assert "999999" not in resp.text


# --- prod config fail-fast guards -------------------------------------------

def _prod(**kw):
    base = dict(app_env="prod", secret_key="real-secret", debug=False,
                cors_origins="https://app.example", _env_file=None)
    base.update(kw)
    return Settings(**base)


def test_prod_allows_a_correct_config() -> None:
    assert _prod().is_production is True


def test_prod_rejects_default_secret() -> None:
    with pytest.raises(ValidationError):
        _prod(secret_key="dev-only-insecure-change-me")


def test_prod_rejects_wildcard_cors() -> None:
    with pytest.raises(ValidationError):
        _prod(cors_origins="*")


def test_prod_rejects_debug() -> None:
    with pytest.raises(ValidationError):
        _prod(debug=True)


def test_docs_disabled_in_prod() -> None:
    assert _prod().docs_enabled is False
    # ... but a non-prod boot still serves them.
    dev = Settings(app_env="dev", _env_file=None)
    assert dev.docs_enabled is True

"""Phase 0 backend test: /health + request-id middleware (PHASE_0 task 9)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_request_id_header_present() -> None:
    resp = client.get("/health")
    assert resp.headers.get("X-Request-ID")


def test_request_id_is_honoured() -> None:
    resp = client.get("/health", headers={"X-Request-ID": "trace-123"})
    assert resp.headers["X-Request-ID"] == "trace-123"


def test_model_version_endpoint() -> None:
    resp = client.get("/meta/model-version")
    assert resp.status_code == 200
    assert "model_version" in resp.json()

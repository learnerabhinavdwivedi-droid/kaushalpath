"""Phase 2 assessment API integration tests.

Drive the real FastAPI routes against a throwaway SQLite DB (dependency
override, so the dev database is never touched). Covers the full resumable
flow: intake constraints -> adaptive answering -> finished profile, plus the
income_band write and answer validation.
"""
from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import get_db
from app.main import app


@pytest.fixture()
def client(tmp_path: Path) -> Iterator[TestClient]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )
    from app.db.base import Base

    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, expire_on_commit=False, future=True)

    def override_get_db():
        db = TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def _answer_body(item: dict, section: str, assessment_id: int) -> dict:
    if section == "interest":
        answer = 5
    else:
        answer = item["options"][0]
    return {"assessment_id": assessment_id, "item_id": item["id"], "answer": answer}


def test_assessment_full_flow_to_profile(client: TestClient) -> None:
    r = client.post(
        "/assessment/student",
        params={"student_id": 1},
        json={
            "edu_level": "12th",
            "district": "Kanpur",
            "state": "UP",
            "income_band": "lt_1l",
            "language": "en",
        },
    )
    assert r.status_code == 201, r.text

    r = client.get("/assessment/next", params={"student_id": 1})
    assert r.status_code == 200, r.text
    body = r.json()
    assessment_id = body["assessment_id"]
    assert body["item"]["section"] == "interest"
    assert body["done"] is False

    steps = 0
    while not body["done"] and steps < 60:
        section = body["item"]["section"]
        payload = _answer_body(body["item"], section, assessment_id)
        r = client.post("/assessment/answer", json=payload)
        assert r.status_code == 200, r.text
        body = r.json()
        steps += 1

    assert body["done"] is True
    assert body["status"] == "completed"

    r = client.get("/assessment/result", params={"student_id": 1})
    assert r.status_code == 200, r.text
    profile = r.json()
    assert profile["status"] == "completed"
    assert len(profile["top3_code"]) == 3
    assert all(0.0 <= v <= 1.0 for v in profile["riasec"].values())
    assert all(0.0 <= v <= 1.0 for v in profile["aptitude"].values())
    assert 0.0 <= profile["confidence"] <= 1.0
    # interest section stopped within the spec budget
    assert profile["items_answered"] <= 24 + 20  # interest(<=24) + aptitude(20)


def test_assessment_income_band_persisted(client: TestClient) -> None:
    client.post(
        "/assessment/student",
        params={"student_id": 2},
        json={"edu_level": "10th", "district": "X", "state": "Y", "income_band": "1l_3l"},
    )
    # re-submitting an update must not error and should keep the student resumable
    r = client.post(
        "/assessment/student",
        params={"student_id": 2},
        json={"edu_level": "10th", "district": "X", "state": "Y", "income_band": "gt_6l"},
    )
    assert r.status_code == 201
    assert r.json()["income_band"] == "gt_6l"


def test_assessment_invalid_income_band_rejected(client: TestClient) -> None:
    r = client.post(
        "/assessment/student",
        params={"student_id": 3},
        json={"edu_level": "12th", "district": "X", "state": "Y", "income_band": "rich"},
    )
    assert r.status_code == 422  # pydantic field_validator


def test_assessment_resumable_next(client: TestClient) -> None:
    client.post(
        "/assessment/student",
        params={"student_id": 4},
        json={"edu_level": "12th", "district": "X", "state": "Y"},
    )
    a = client.get("/assessment/next", params={"student_id": 4}).json()
    b = client.get("/assessment/next", params={"assessment_id": a["assessment_id"]}).json()
    # calling /next again without answering returns the same pending item
    assert a["item"]["id"] == b["item"]["id"]


def test_assessment_answer_validation(client: TestClient) -> None:
    client.post(
        "/assessment/student",
        params={"student_id": 5},
        json={"edu_level": "12th", "district": "X", "state": "Y"},
    )
    body = client.get("/assessment/next", params={"student_id": 5}).json()
    aid = body["assessment_id"]
    # out-of-range interest answer
    r = client.post(
        "/assessment/answer",
        json={"assessment_id": aid, "item_id": body["item"]["id"], "answer": 9},
    )
    assert r.status_code == 400
    # stale item id (answer targets a different item than the pending one)
    r = client.post(
        "/assessment/answer",
        json={"assessment_id": aid, "item_id": "R99", "answer": 3},
    )
    assert r.status_code == 400


def test_assessment_restart_abandons_open_session(client: TestClient) -> None:
    client.post(
        "/assessment/student",
        params={"student_id": 6},
        json={"edu_level": "12th", "district": "X", "state": "Y"},
    )
    first = client.get("/assessment/next", params={"student_id": 6}).json()["assessment_id"]
    again = client.post("/assessment/session", params={"student_id": 6, "restart": True}).json()
    assert again["assessment_id"] != first
    assert again["items_answered"] == 0

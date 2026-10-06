"""Integration tests for Phase 13 Resistance Analytics API,
suppression, role scoping, and export.
"""
from __future__ import annotations

import csv
import io

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.student import Student
from app.models.user import User


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str, role: str) -> dict:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_role_scoping_scheme_admin_and_admin(client_with_db) -> None:
    client = client_with_db

    scheme_admin = _register(client, "sadmin@example.com", "scheme_admin")["access_token"]
    sys_admin = _register(client, "admin@example.com", "admin")["access_token"]
    counsellor = _register(client, "couns@example.com", "counsellor")["access_token"]
    student = _register(client, "stud@example.com", "student")["access_token"]

    # 1. scheme_admin and admin must succeed
    res_sadmin = client.get("/admin/resistance", headers=_auth(scheme_admin))
    assert res_sadmin.status_code == 200

    res_admin = client.get("/admin/resistance", headers=_auth(sys_admin))
    assert res_admin.status_code == 200

    # 2. counsellor and student must be forbidden (403)
    res_couns = client.get("/admin/resistance", headers=_auth(counsellor))
    assert res_couns.status_code == 403

    res_stud = client.get("/admin/resistance", headers=_auth(student))
    assert res_stud.status_code == 403


def test_small_group_suppression(client_with_db, db_session: Session) -> None:
    client = client_with_db
    token = _register(client, "sa_suppress@example.com", "scheme_admin")["access_token"]

    # Create students in two districts:
    # District A has 6 conversations (>= 5 -> kept)
    # District B has 2 conversations (< 5 -> suppressed)
    u_a = User(email="ua@example.com", hashed_password="pw", role="student")
    u_b = User(email="ub@example.com", hashed_password="pw", role="student")
    db_session.add_all([u_a, u_b])
    db_session.flush()

    s_a = Student(
        user_id=u_a.id,
        district="DistrictA",
        state="StateA",
        edu_level="10th",
        budget_band="low",
        relocate_ok=True,
        language="hi",
    )
    s_b = Student(
        user_id=u_b.id,
        district="DistrictB",
        state="StateB",
        edu_level="10th",
        budget_band="low",
        relocate_ok=True,
        language="hi",
    )
    db_session.add_all([s_a, s_b])
    db_session.flush()

    # 6 conversations for District A
    for _ in range(6):
        c = Conversation(student_id=s_a.id, lang="hi", status="active")
        db_session.add(c)
        db_session.flush()
        t = Turn(
            conversation_id=c.id,
            speaker="parent",
            text="Q",
            lang="hi",
            sentiment="negative",
            intensity=0.5,
            topic="safety",
        )
        db_session.add(t)
        db_session.flush()
        db_session.add(ResistanceSnapshot(conversation_id=c.id, turn_id=t.id, rs=0.65))

    # 2 conversations for District B
    for _ in range(2):
        c = Conversation(student_id=s_b.id, lang="hi", status="active")
        db_session.add(c)
        db_session.flush()
        t = Turn(
            conversation_id=c.id,
            speaker="parent",
            text="Q",
            lang="hi",
            sentiment="negative",
            intensity=0.4,
            topic="cost",
        )
        db_session.add(t)
        db_session.flush()
        db_session.add(ResistanceSnapshot(conversation_id=c.id, turn_id=t.id, rs=0.45))

    db_session.commit()

    # Query /admin/resistance
    res = client.get("/admin/resistance?group_by=district", headers=_auth(token))
    assert res.status_code == 200
    data = res.json()

    # DistrictA must be present in groups
    group_keys = [g["key"] for g in data["groups"]]
    assert "DistrictA" in group_keys

    # DistrictB (< 5) must be suppressed
    assert "DistrictB" not in group_keys
    assert data["suppressed_groups"] >= 1


def test_resistance_timeseries_and_map(client_with_db, db_session: Session) -> None:
    client = client_with_db
    token = _register(client, "sa_map@example.com", "scheme_admin")["access_token"]

    # Timeseries endpoint
    res_ts = client.get("/admin/resistance/timeseries", headers=_auth(token))
    assert res_ts.status_code == 200
    assert "timeseries" in res_ts.json()

    # Map endpoint
    res_map = client.get("/admin/resistance/map", headers=_auth(token))
    assert res_map.status_code == 200
    map_data = res_map.json()
    assert "map_points" in map_data
    assert "suppressed_districts" in map_data


def test_resistance_export_csv(client_with_db) -> None:
    client = client_with_db
    token = _register(client, "sa_csv@example.com", "scheme_admin")["access_token"]

    res = client.get("/admin/resistance/export.csv", headers=_auth(token))
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]

    csv_reader = csv.reader(io.StringIO(res.text))
    rows = list(csv_reader)
    assert len(rows) >= 1  # Header row present

    header = rows[0]
    expected_headers = [
        "conversation_id",
        "student_id",
        "district",
        "state",
        "trade",
        "shift_label",
        "avg_rs",
        "high_resistance",
        "created_at",
    ]
    assert header == expected_headers

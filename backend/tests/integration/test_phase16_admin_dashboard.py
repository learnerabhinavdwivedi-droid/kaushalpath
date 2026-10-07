"""Integration tests for the Phase 16 scheme-administrator resistance dashboard.

Covers role scoping, the KPI strip, small-group (k<5) suppression, the
concern x trade matrix, filters and the demo flag. Existing Phase 13
endpoints are untouched; these tests only exercise the new
``GET /admin/resistance/dashboard`` aggregation.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.human import Escalation
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


def _seed_conversation(
    db: Session, student: Student, topic: str, rs: float, sentiment: str = "negative"
) -> Conversation:
    c = Conversation(student_id=student.id, lang="hi", status="active")
    db.add(c)
    db.flush()
    for _ in range(3):
        t = Turn(
            conversation_id=c.id,
            speaker="parent",
            text="Mujhe safety ki chinta hai",
            lang="hi",
            sentiment=sentiment,
            intensity=0.6,
            topic=topic,
        )
        db.add(t)
        db.flush()
        db.add(ResistanceSnapshot(conversation_id=c.id, turn_id=t.id, rs=rs))
    return c


def test_dashboard_role_scoping(client_with_db) -> None:
    client = client_with_db
    scheme_admin = _register(client, "sa_dash@example.com", "scheme_admin")["access_token"]
    sys_admin = _register(client, "admin_dash@example.com", "admin")["access_token"]
    counsellor = _register(client, "couns_dash@example.com", "counsellor")["access_token"]

    ok_s = client.get("/admin/resistance/dashboard", headers=_auth(scheme_admin))
    assert ok_s.status_code == 200
    ok_a = client.get("/admin/resistance/dashboard", headers=_auth(sys_admin))
    assert ok_a.status_code == 200
    blocked = client.get("/admin/resistance/dashboard", headers=_auth(counsellor))
    assert blocked.status_code == 403


def test_dashboard_suppression_and_kpis(client_with_db, db_session: Session) -> None:
    client = client_with_db
    token = _register(client, "sa_kpi@example.com", "scheme_admin")["access_token"]

    # District A: 6 conversations (kept). District B: 2 conversations (suppressed).
    u_a = User(email="kpi_a@example.com", hashed_password="pw", role="student")
    u_b = User(email="kpi_b@example.com", hashed_password="pw", role="student")
    db_session.add_all([u_a, u_b])
    db_session.flush()
    s_a = Student(user_id=u_a.id, district="DistrictA", state="StateA", edu_level="10th")
    s_b = Student(user_id=u_b.id, district="DistrictB", state="StateB", edu_level="10th")
    db_session.add_all([s_a, s_b])
    db_session.flush()

    for _ in range(6):
        _seed_conversation(db_session, s_a, topic="safety", rs=0.70)
    for _ in range(2):
        _seed_conversation(db_session, s_b, topic="cost", rs=0.30)

    # One escalation on a District A conversation -> escalation_rate > 0.
    first_a = db_session.query(Conversation).filter_by(student_id=s_a.id).first()
    db_session.add(
        Escalation(
            conversation_id=first_a.id,
            raised_by_user_id=u_a.id,
            student_id=s_a.id,
            reason="Safety concerns unresolved",
            status="open",
        )
    )
    db_session.commit()

    data = client.get("/admin/resistance/dashboard", headers=_auth(token)).json()

    kpis = data["kpis"]
    assert kpis["families_counselled"] >= 2
    assert kpis["total_conversations"] >= 8
    assert kpis["pct_high_resistance"] > 0
    assert kpis["top_concern"] == "safety"
    assert kpis["escalation_rate"] > 0

    by_name = {d["district"]: d for d in data["districts"]}
    assert by_name["DistrictA"]["is_suppressed"] is False
    assert by_name["DistrictA"]["avg_rs"] is not None
    # District B (n=2 < 5): suppressed -> avg_rs redacted.
    assert by_name["DistrictB"]["is_suppressed"] is True
    assert by_name["DistrictB"]["avg_rs"] is None
    assert data["suppressed_groups"] >= 1

    matrix = data["matrix"]
    assert len(matrix["cells"]) == len(matrix["concerns"])
    assert all(len(row) == len(matrix["trades"]) for row in matrix["cells"])

    assert data["is_demo"] is True


def test_dashboard_state_filter(client_with_db, db_session: Session) -> None:
    client = client_with_db
    token = _register(client, "sa_filter@example.com", "scheme_admin")["access_token"]

    u = User(email="filter_a@example.com", hashed_password="pw", role="student")
    db_session.add(u)
    db_session.flush()
    s = Student(user_id=u.id, district="FilterDistrict", state="FilterState", edu_level="12th")
    db_session.add(s)
    db_session.flush()
    for _ in range(6):
        _seed_conversation(db_session, s, topic="income", rs=0.55)
    db_session.commit()

    only_state = client.get(
        "/admin/resistance/dashboard?state=FilterState", headers=_auth(token)
    ).json()
    names = {d["district"] for d in only_state["districts"]}
    assert "FilterDistrict" in names

    other = client.get(
        "/admin/resistance/dashboard?state=NoSuchState", headers=_auth(token)
    ).json()
    assert other["kpis"]["total_conversations"] == 0
    assert other["districts"] == []

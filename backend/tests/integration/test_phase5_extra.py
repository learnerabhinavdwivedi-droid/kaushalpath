"""Phase 5: expanded integration tests — refresh, compare, roadmap, cohort,
override, escalation, and authorisation failures."""
from __future__ import annotations

from app.models.occupation import Occupation
from app.models.student import Student
from app.models.user import User


def _register(client, email, role):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_occupations(db, n=2):
    rows = []
    for i in range(1, n + 1):
        occ = Occupation(name_en=f"Occupation {i}", source="test", is_demo=True, nsqf_level=3)
        db.add(occ)
        rows.append(occ)
    db.commit()
    for occ in rows:
        db.refresh(occ)
    return [occ.id for occ in rows]


def test_auth_me_resolves_student(client_with_db):
    client = client_with_db
    token = _register(client, "me@test.com", "student")["access_token"]
    me = client.get("/auth/me", headers=_auth(token))
    assert me.status_code == 200, me.text
    body = me.json()
    assert body["role"] == "student"
    assert body["student_id"] is not None

    coun = _register(client, "mec@test.com", "counsellor")["access_token"]
    me2 = client.get("/auth/me", headers=_auth(coun)).json()
    assert me2["student_id"] is None


def test_auth_refresh_flow(client_with_db):
    client = client_with_db
    _register(client, "stu@test.com", "student")
    login = client.post(
        "/auth/login", data={"username": "stu@test.com", "password": "password"}
    )
    assert login.status_code == 200, login.text
    refresh_token = login.json()["refresh_token"]

    refreshed = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["access_token"]

    # An access token (no `refresh` claim) must not be accepted as a refresh token.
    access = refreshed.json()["access_token"]
    bad = client.post("/auth/refresh", json={"refresh_token": access})
    assert bad.status_code == 401


def test_compare_and_roadmap(client_with_db, db_session):
    client = client_with_db
    occ_ids = _seed_occupations(db_session)

    student_token = _register(client, "s2@test.com", "student")["access_token"]
    parent_token = _register(client, "p2@test.com", "parent")["access_token"]

    room = client.post("/rooms", headers=_auth(student_token)).json()["code"]
    client.post(f"/rooms/{room}/join", headers=_auth(parent_token))

    client.put(
        f"/rooms/{room}/weights",
        headers=_auth(student_token),
        json={"cost": 1.0, "duration": 0.0, "salary": 1.0, "local_jobs": 0.0, "distance": 0.0},
    )

    resp = client.post(
        f"/rooms/{room}/compare", headers=_auth(student_token), json={"occupation_ids": occ_ids}
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data["results"]) == 2
    assert set(data["results"][0]["criteria"]) == {
        "cost",
        "duration",
        "salary",
        "local_jobs",
        "distance",
    }
    assert "disagreement" in data

    roadmap = client.get(f"/roadmap/{occ_ids[0]}?district=Pune", headers=_auth(student_token))
    assert roadmap.status_code == 200, roadmap.text
    body = roadmap.json()
    assert body["occupation_id"] == occ_ids[0]
    assert len(body["steps"]) == 5
    assert "source" in body and "is_demo" in body

    missing = client.get("/roadmap/999999", headers=_auth(student_token))
    assert missing.status_code == 404


def test_cohort_override_and_escalation(client_with_db, db_session):
    client = client_with_db
    occ_ids = _seed_occupations(db_session, n=1)

    admin_token = _register(client, "admin@test.com", "admin")["access_token"]
    counsellor_token = _register(client, "coun@test.com", "counsellor")["access_token"]
    other_counsellor_token = _register(client, "coun2@test.com", "counsellor")["access_token"]
    student_token = _register(client, "s3@test.com", "student")["access_token"]

    room = client.post("/rooms", headers=_auth(student_token)).json()["code"]
    counsellor_id = db_session.query(User).filter(User.email == "coun@test.com").first().id
    student_id = db_session.query(Student).filter(Student.district == "Unknown").first().id

    # Escalation raised before assignment (counsellor not yet linked).
    esc = client.post(
        f"/rooms/{room}/escalate",
        headers=_auth(student_token),
        json={"reason": "AI answer unclear", "occupation_id": occ_ids[0]},
    )
    assert esc.status_code == 200, esc.text
    esc_id = esc.json()["id"]

    # Empty cohort before assignment.
    assert client.get("/counsellor/cohort", headers=_auth(counsellor_token)).json() == []

    # Admin assigns counsellor to the student.
    assign = client.post(
        "/counsellor/assign",
        headers=_auth(admin_token),
        json={"counsellor_id": counsellor_id, "student_id": student_id},
    )
    assert assign.status_code == 200, assign.text

    # Counsellor now sees the cohort and the backfilled escalation.
    cohort = client.get("/counsellor/cohort", headers=_auth(counsellor_token)).json()
    assert any(c["student_id"] == student_id for c in cohort)

    queue = client.get("/counsellor/escalations", headers=_auth(counsellor_token)).json()
    assert any(e["id"] == esc_id for e in queue)

    # Override persists with an audit trail.
    override = client.post(
        "/counsellor/override",
        headers=_auth(counsellor_token),
        json={"student_id": student_id, "occupation_id": occ_ids[0], "note": "Manual pick"},
    )
    assert override.status_code == 200, override.text
    assert override.json()["override_id"]
    assert "created_at" in override.json()["audit"]

    # A counsellor without the student in cohort cannot override.
    denied = client.post(
        "/counsellor/override",
        headers=_auth(other_counsellor_token),
        json={"student_id": student_id, "occupation_id": occ_ids[0], "note": "nope"},
    )
    assert denied.status_code == 403

    # Non-counsellor cannot read the cohort.
    assert client.get("/counsellor/cohort", headers=_auth(student_token)).status_code == 403

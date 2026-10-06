"""Integration tests for Phase 14 Human Escalation (PSID 26241).

Covers the acceptance gate in the gap-analysis plan:
* unassigned escalation lands in the shared pool and is visible to counsellors;
* claim is atomic (two counsellors cannot take the same case);
* the case pack carries the last turns, topics, latest Rs, shortlisted trades
  and family context;
* the lifecycle open -> assigned -> contacted -> resolved is enforced;
* family isolation (a counsellor only sees their own + the pool).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.centre import Centre
from app.models.course import Course
from app.models.market import Market
from app.models.occupation import Occupation
from app.models.provider_outcome import ProviderOutcome
from app.models.recommendation import Recommendation


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _register(client, email: str, role: str) -> dict:
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password123", "role": role, "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    token = data["access_token"]
    me = client.get("/auth/me", headers=_auth(token)).json()
    data["student_id"] = me.get("student_id")
    data["user_id"] = me["user_id"]
    return data


def _setup_trade_data(db: Session) -> Occupation:
    occ = Occupation(
        name_en="Electrician",
        name_hi="इलेक्ट्रीशियन",
        is_vocational=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db.add(occ)
    db.flush()
    course = Course(
        occupation_id=occ.id,
        name="ITI Electrician",
        nsqf_level=4,
        fee_inr=4500,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db.add(course)
    db.flush()
    centre = Centre(
        course_id=course.id,
        name="Govt ITI Varanasi",
        district="Varanasi",
        state="Uttar Pradesh",
        provider_type="Government ITI",
        has_female_trainers=True,
        has_hostel=True,
        safety_certified=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db.add(centre)
    db.flush()
    db.add(
        ProviderOutcome(
            provider_id=centre.id,
            course_id=course.id,
            cohort_year=2025,
            enrolled=80,
            certified=75,
            placed=62,
            placement_rate=82.7,
            earnings_median=19500,
            earnings_p25=16000,
            earnings_p75=25000,
            source="demo_synth_2026",
            source_year=2026,
            is_demo=True,
        )
    )
    db.add(
        Market(
            occupation_id=occ.id,
            state="Uttar Pradesh",
            district="Varanasi",
            avg_salary_inr=19500,
            earnings_p25=16000,
            earnings_p75=25000,
            placement_rate=82.7,
            source="demo_synth_2026",
            source_year=2026,
            is_demo=True,
        )
    )
    db.commit()
    db.refresh(occ)
    return occ


def _escalate(client, student_token, student_id, occ, reason):
    """Create a conversation, post a turn, and raise an escalation. Returns ack."""
    conv = client.post(
        "/conversations",
        json={"student_id": student_id, "lang": "hi"},
        headers=_auth(student_token),
    ).json()
    conv_id = conv["id"]
    turn_body = {
        "speaker": "parent",
        "text": "बेटी के लिए यह सुरक्षित नहीं है, मुझे किसी अधिकारी से बात करनी है",
    }
    if occ is not None:
        turn_body["occupation_id"] = occ.id
    client.post(
        f"/conversations/{conv_id}/turns",
        json=turn_body,
        headers=_auth(student_token),
    )
    ack = client.post(
        f"/conversations/{conv_id}/escalate",
        json={"reason": reason, "contact_phone": "9876543210"},
        headers=_auth(student_token),
    )
    assert ack.status_code == 201, ack.text
    return ack.json()


def test_pool_visibility_and_atomic_claim(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)

    stu = _register(client, "stu14a@example.com", "student")
    _register(client, "cA14@example.com", "counsellor")
    _register(client, "cB14@example.com", "counsellor")

    # No counsellor is assigned -> the case must land in the shared pool.
    ack = _escalate(client, stu["access_token"], stu["student_id"], occ, "safety concern")
    assert ack["in_pool"] is True
    assert ack["assigned_counsellor_id"] is None
    esc_id = ack["id"]

    # A counsellor (not the owner) can now see it in their queue.
    login = client.post(
        "/auth/login",
        data={"username": "cA14@example.com", "password": "password123"},
    )
    cA_token = login.json()["access_token"]
    queue = client.get("/counsellor/escalations", headers=_auth(cA_token)).json()
    assert any(e["id"] == esc_id and e["in_pool"] for e in queue)

    # cA claims it.
    claim = client.post(f"/counsellor/escalations/{esc_id}/claim", headers=_auth(cA_token))
    assert claim.status_code == 200, claim.text
    assert claim.json()["status"] == "assigned"
    assert claim.json()["claimed_at"] is not None

    # cB tries to claim the same case -> conflict.
    login_b = client.post(
        "/auth/login",
        data={"username": "cB14@example.com", "password": "password123"},
    )
    cB_token = login_b.json()["access_token"]
    second = client.post(f"/counsellor/escalations/{esc_id}/claim", headers=_auth(cB_token))
    assert second.status_code == 409


def test_lifecycle_contact_resolve(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)
    stu = _register(client, "stu14b@example.com", "student")
    admin = _register(client, "admin14@example.com", "admin")
    coun = _register(client, "coun14@example.com", "counsellor")

    # Route the case to a specific counsellor via an admin assignment first.
    assign = client.post(
        "/counsellor/assign",
        json={"counsellor_id": coun["user_id"], "student_id": stu["student_id"]},
        headers=_auth(admin["access_token"]),
    )
    assert assign.status_code == 200, assign.text

    ack = _escalate(client, stu["access_token"], stu["student_id"], occ, "income objection")
    # auto_route soft-assigned the only cohort counsellor -> status already assigned.
    assert ack["assigned_counsellor_id"] == coun["user_id"]
    assert ack["in_pool"] is False
    assert ack["status"] == "assigned"
    esc_id = ack["id"]

    # The owning counsellor progresses the lifecycle: contact -> resolve.
    contact = client.post(
        f"/counsellor/escalations/{esc_id}/contact", headers=_auth(coun["access_token"])
    )
    assert contact.status_code == 200, contact.text
    assert contact.json()["status"] == "contacted"
    assert contact.json()["contacted_at"] is not None

    note = client.post(
        f"/counsellor/escalations/{esc_id}/notes",
        json={"note": "Called the family, will visit the centre."},
        headers=_auth(coun["access_token"]),
    )
    assert note.status_code == 200, note.text
    assert "Called the family" in note.json()["notes"]

    resolve = client.post(
        f"/counsellor/escalations/{esc_id}/resolve", headers=_auth(coun["access_token"])
    )
    assert resolve.status_code == 200, resolve.text
    assert resolve.json()["status"] == "resolved"
    assert resolve.json()["resolved_at"] is not None

    # Resolving twice is rejected.
    again = client.post(
        f"/counsellor/escalations/{esc_id}/resolve", headers=_auth(coun["access_token"])
    )
    assert again.status_code == 409


def test_case_pack_contents(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)
    stu = _register(client, "stu14c@example.com", "student")

    # Give the student a shortlisted recommendation so the pack has a trade.
    db_session.add(
        Recommendation(
            student_id=stu["student_id"],
            occupation_id=occ.id,
            rank=1,
            score=0.9,
            reasons_json=["vocational_fit"],
        )
    )
    db_session.commit()

    ack = _escalate(client, stu["access_token"], stu["student_id"], occ, "pack check")
    pack = ack["case_pack"]
    assert pack is not None
    for key in ("last_turns", "topics", "shortlisted_trades", "family_context", "latest_rs"):
        assert key in pack
    assert len(pack["last_turns"]) >= 1
    assert pack["shortlisted_trades"], "expected at least one shortlisted trade"
    assert pack["shortlisted_trades"][0]["name_en"] == "Electrician"
    assert pack["family_context"]["district"] == "Unknown"


def test_family_isolation_on_queue(client_with_db, db_session: Session) -> None:
    client = client_with_db
    _setup_trade_data(db_session)
    stu = _register(client, "stu14d@example.com", "student")
    other = _register(client, "stu14e@example.com", "student")

    _escalate(client, stu["access_token"], stu["student_id"], None, "iso case")

    # A different family (student) has no counsellor access to the queue.
    forbidden = client.get("/counsellor/escalations", headers=_auth(other["access_token"]))
    assert forbidden.status_code == 403

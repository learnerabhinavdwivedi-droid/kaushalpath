"""Integration tests for Phase 12 Conversational Engine (PSID 26241).

Tests:
1. Full conversation turn in Hindi (persisted, grounded facts, reply structure).
2. Full conversation turn in English (placement facts, followups).
3. Hallucination rejection stub test (invented salary rejected, template fallback used).
4. Authorization & room isolation (unauthorized users get 403).
5. Escalation flow (user requesting human counsellor triggers escalation_suggested and status).
6. Auto-trigger: two consecutive unresolved (negative) family turns raise
   escalation_suggested via the Phase 14 should_escalate service (no explicit ask).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.centre import Centre
from app.models.course import Course
from app.models.market import Market
from app.models.occupation import Occupation
from app.models.provider_outcome import ProviderOutcome
from app.services.conversation.responder import generate_response


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
        transport_note="Direct public buses available.",
        safety_certified=True,
        source="demo_synth_2026",
        source_year=2026,
        is_demo=True,
    )
    db.add(centre)
    db.flush()

    po = ProviderOutcome(
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
    db.add(po)

    market = Market(
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
    db.add(market)
    db.commit()
    db.refresh(occ)
    return occ


def test_full_turn_hi(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)

    # Register student
    reg = _register(client, "student_hi@example.com", "student")
    token = reg["access_token"]
    student_id = reg["student_id"]

    # 1. Create conversation
    create_res = client.post(
        "/conversations",
        json={"student_id": student_id, "lang": "hi"},
        headers=_auth(token),
    )
    assert create_res.status_code == 201, create_res.text
    conv_id = create_res.json()["id"]

    # 2. Post a Hindi parental turn inquiring about salary
    turn_res = client.post(
        f"/conversations/{conv_id}/turns",
        json={
            "speaker": "parent",
            "text": "इस ट्रेड में प्रशिक्षण के बाद शुरुआती वेतन कितना मिलता है?",
            "occupation_id": occ.id,
        },
        headers=_auth(token),
    )
    assert turn_res.status_code == 200, turn_res.text
    data = turn_res.json()

    assert data["lang"] == "hi"
    assert data["topic"] == "income"
    assert data["intent"] in ("inquire", "object")
    assert data["fallback_used"] is False
    assert len(data["facts"]) > 0
    assert len(data["followups"]) > 0

    # Ensure facts have required schema keys
    for f in data["facts"]:
        for k in ("key", "label", "value", "unit", "source", "source_year", "is_demo"):
            assert k in f

    # Ensure DB persisted both user turn and assistant reply
    conv_get = client.get(f"/conversations/{conv_id}", headers=_auth(token))
    assert conv_get.status_code == 200
    turns = conv_get.json()["turns"]
    assert len(turns) == 2
    assert turns[0]["speaker"] == "parent"
    assert turns[1]["speaker"] == "assistant"
    assert turns[1]["facts_json"] is not None


def test_full_turn_en(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)

    reg = _register(client, "student_en@example.com", "student")
    token = reg["access_token"]
    student_id = reg["student_id"]

    # Create conversation
    create_res = client.post(
        "/conversations",
        json={"student_id": student_id, "lang": "en"},
        headers=_auth(token),
    )
    assert create_res.status_code == 201
    conv_id = create_res.json()["id"]

    # Post an English inquiry about job security/placement
    turn_res = client.post(
        f"/conversations/{conv_id}/turns",
        json={
            "speaker": "learner",
            "text": "What is the placement rate and job security at this college?",
            "occupation_id": occ.id,
        },
        headers=_auth(token),
    )
    assert turn_res.status_code == 200, turn_res.text
    data = turn_res.json()

    assert data["lang"] == "en"
    assert data["topic"] == "security"
    assert "82.7" in data["reply"] or "82" in data["reply"]
    assert data["fallback_used"] is False


def test_hallucination_stub_rejected(db_session: Session) -> None:
    """Gate test: A stub LLM returning an invented salary is rejected and fallback is used."""
    occ = _setup_trade_data(db_session)
    from app.services.conversation.grounder import ground_facts

    facts = ground_facts(db=db_session, occupation_id=occ.id)

    def stub_llm_hallucinator(template: str, facts: list, lang: str) -> str:
        # Returns an invented salary of 95,000 INR
        return "The starting salary after this course is ₹95,000 per month."

    res = generate_response(
        topic="income",
        lang="en",
        facts=facts,
        llm_rephraser=stub_llm_hallucinator,
    )

    # Hallucination MUST be rejected and template fallback used
    assert res["fallback_used"] is True
    assert "95,000" not in res["reply"]
    assert "19,500" in res["reply"] or "19500" in res["reply"]


def test_room_isolation_and_authorization(client_with_db, db_session: Session) -> None:
    client = client_with_db
    _setup_trade_data(db_session)

    reg_owner = _register(client, "owner@example.com", "student")
    owner_token = reg_owner["access_token"]
    owner_stu_id = reg_owner["student_id"]

    reg_other = _register(client, "intruder@example.com", "student")
    other_token = reg_other["access_token"]

    # Owner creates conversation
    conv_res = client.post(
        "/conversations",
        json={"student_id": owner_stu_id},
        headers=_auth(owner_token),
    )
    assert conv_res.status_code == 201
    conv_id = conv_res.json()["id"]

    # Intruder tries to read owner's conversation
    forbidden_get = client.get(f"/conversations/{conv_id}", headers=_auth(other_token))
    assert forbidden_get.status_code == 403

    # Intruder tries to post turn to owner's conversation
    forbidden_post = client.post(
        f"/conversations/{conv_id}/turns",
        json={"speaker": "learner", "text": "Can I read this?"},
        headers=_auth(other_token),
    )
    assert forbidden_post.status_code == 403


def test_escalation_suggestion_flow(client_with_db, db_session: Session) -> None:
    client = client_with_db
    occ = _setup_trade_data(db_session)

    reg = _register(client, "escalate_stu@example.com", "student")
    token = reg["access_token"]
    student_id = reg["student_id"]

    conv_res = client.post(
        "/conversations",
        json={"student_id": student_id},
        headers=_auth(token),
    )
    conv_id = conv_res.json()["id"]

    # Explicit request to talk to human counsellor
    turn_res = client.post(
        f"/conversations/{conv_id}/turns",
        json={
            "speaker": "parent",
            "text": "I want to talk directly to a human counsellor right now",
            "occupation_id": occ.id,
        },
        headers=_auth(token),
    )
    assert turn_res.status_code == 200
    data = turn_res.json()

    assert data["intent"] == "escalate"
    assert data["escalation_suggested"] is True

    # Verify conversation status was escalated
    conv_data = client.get(f"/conversations/{conv_id}", headers=_auth(token)).json()
    assert conv_data["status"] == "escalated"


def test_auto_trigger_two_unresolved_turns(client_with_db, db_session: Session) -> None:
    """Phase 14: the route auto-suggests escalation after 2 negative family turns."""
    client = client_with_db
    occ = _setup_trade_data(db_session)

    reg = _register(client, "autotrigger_stu@example.com", "student")
    token = reg["access_token"]
    student_id = reg["student_id"]

    conv_id = client.post(
        "/conversations", json={"student_id": student_id}, headers=_auth(token)
    ).json()["id"]

    # Turn 1: a worried, negative parent objection (no explicit request for a human).
    first = client.post(
        f"/conversations/{conv_id}/turns",
        json={
            "speaker": "parent",
            "text": "This pay is never enough, I am very worried and against it",
            "occupation_id": occ.id,
        },
        headers=_auth(token),
    )
    assert first.status_code == 200

    # Turn 2: a second consecutive negative family turn crosses the auto-trigger.
    second = client.post(
        f"/conversations/{conv_id}/turns",
        json={
            "speaker": "parent",
            "text": "Absolutely not, this job is insecure and I strongly disagree",
            "occupation_id": occ.id,
        },
        headers=_auth(token),
    )
    assert second.status_code == 200
    assert second.json()["escalation_suggested"] is True

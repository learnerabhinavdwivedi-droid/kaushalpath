"""Phase 18: right-to-erasure cascade.

`DELETE /auth/students/me` must remove the conversational trail (conversations,
turns, resistance snapshots, escalations), not just the account. SQLite FK
enforcement is off, so this verifies the endpoint's explicit cascade.
"""
from __future__ import annotations

from app.models import (
    Conversation,
    Escalation,
    ResistanceSnapshot,
    Turn,
    User,
)


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _register(client, email):
    resp = client.post(
        "/auth/register",
        json={"email": email, "password": "password", "role": "student", "give_consent": True},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def test_delete_my_data_cascades_conversations_turns_snapshots_escalations(
    client_with_db, db_session
):
    client = client_with_db
    token = _register(client, "erase@t.com")
    me = client.get("/auth/me", headers=_auth(token)).json()
    sid = me["student_id"]
    uid = me["user_id"]

    # Seed one conversation with two turns, a resistance snapshot on each turn,
    # and an escalation raised from it.
    conv = Conversation(student_id=sid, lang="hi", status="active")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)

    t1 = Turn(
        conversation_id=conv.id,
        speaker="parent",
        text="low pay",
        lang="hi",
        topic="income",
    )
    t2 = Turn(
        conversation_id=conv.id,
        speaker="assistant",
        text="18,500",
        lang="hi",
        topic="income",
    )
    db_session.add_all([t1, t2])
    db_session.commit()
    db_session.refresh(t1)
    db_session.refresh(t2)

    db_session.add_all(
        [
            ResistanceSnapshot(conversation_id=conv.id, turn_id=t1.id, rs=0.7),
            ResistanceSnapshot(conversation_id=conv.id, turn_id=t2.id, rs=0.6),
        ]
    )
    db_session.add(
        Escalation(
            conversation_id=conv.id,
            raised_by_user_id=uid,
            student_id=sid,
            reason="low_income_objection",
            status="open",
        )
    )
    db_session.commit()

    # Pre-conditions: the trail exists.
    assert db_session.query(Conversation).filter_by(student_id=sid).count() == 1
    assert db_session.query(Turn).filter_by(conversation_id=conv.id).count() == 2
    assert db_session.query(ResistanceSnapshot).filter_by(conversation_id=conv.id).count() == 2
    assert db_session.query(Escalation).filter_by(conversation_id=conv.id).count() == 1

    # Erase.
    assert client.delete("/auth/students/me", headers=_auth(token)).status_code == 200

    # Post-conditions: every conversational row for this student is gone.
    assert db_session.query(Conversation).filter_by(student_id=sid).count() == 0
    assert db_session.query(Turn).filter_by(conversation_id=conv.id).count() == 0
    assert db_session.query(ResistanceSnapshot).filter_by(conversation_id=conv.id).count() == 0
    assert db_session.query(Escalation).filter_by(conversation_id=conv.id).count() == 0
    # And the account itself.
    assert db_session.get(User, uid) is None


def test_delete_my_data_audit_records_non_identifying_counts(client_with_db, db_session):
    import json

    client = client_with_db
    token = _register(client, "eraseaudit@t.com")
    sid = client.get("/auth/me", headers=_auth(token)).json()["student_id"]

    conv = Conversation(student_id=sid, lang="en", status="active")
    db_session.add(conv)
    db_session.commit()
    db_session.refresh(conv)
    db_session.add(Turn(conversation_id=conv.id, speaker="learner", text="hi", lang="en"))
    db_session.commit()

    assert client.delete("/auth/students/me", headers=_auth(token)).status_code == 200

    from app.models import AuditLog

    entry = db_session.query(AuditLog).filter_by(action="data_deletion").one()
    detail = entry.detail
    assert detail["conversations"] == 1
    assert detail["turns"] == 1
    # The trail must not preserve the deleted content itself.
    assert "hi" not in json.dumps(detail)

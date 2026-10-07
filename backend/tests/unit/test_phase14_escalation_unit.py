"""Unit tests for Phase 14 escalation service + notifier (no HTTP layer)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.human import Escalation
from app.models.student import Student
from app.models.user import User
from app.services.escalation_svc import should_escalate
from app.services.notifier import WhatsAppLinkNotifier, _normalise_phone, get_notifier


def _mk_conversation(db: Session) -> Conversation:
    user = User(
        email="u14@example.com",
        hashed_password="x",
        role="student",
        lang="hi",
    )
    db.add(user)
    db.flush()
    student = Student(
        user_id=user.id,
        edu_level="10th",
        district="Varanasi",
        state="Uttar Pradesh",
        language="hi",
    )
    db.add(student)
    db.flush()
    conv = Conversation(student_id=student.id, lang="hi", status="active")
    db.add(conv)
    db.commit()
    return conv


def _add_turn(db: Session, conv: Conversation, **kw) -> Turn:
    turn = Turn(conversation_id=conv.id, speaker="parent", text="t", **kw)
    db.add(turn)
    db.commit()
    db.refresh(turn)
    return turn


def test_should_escalate_explicit_request(db_session: Session) -> None:
    conv = _mk_conversation(db_session)
    _add_turn(db_session, conv, intent="escalate", sentiment="neutral", topic="other")
    escalate, reason = should_escalate(db_session, conv)
    assert escalate is True
    assert reason == "explicit_request"


def test_should_escalate_high_resistance(db_session: Session) -> None:
    conv = _mk_conversation(db_session)
    turn = _add_turn(
        db_session,
        conv,
        intent="object",
        sentiment="negative",
        topic="safety",
        intensity=0.9,
    )
    threshold = get_settings().escalation_rs_threshold
    db_session.add(ResistanceSnapshot(conversation_id=conv.id, turn_id=turn.id, rs=threshold + 0.1))
    db_session.commit()
    escalate, reason = should_escalate(db_session, conv)
    assert escalate is True
    assert reason == "high_resistance"


def test_should_escalate_two_unresolved(db_session: Session) -> None:
    conv = _mk_conversation(db_session)
    _add_turn(db_session, conv, intent="object", sentiment="negative", topic="income")
    _add_turn(db_session, conv, intent="object", sentiment="concern", topic="cost")
    escalate, reason = should_escalate(db_session, conv)
    assert escalate is True
    assert reason == "two_unresolved_turns"


def test_should_not_escalate_when_positive(db_session: Session) -> None:
    conv = _mk_conversation(db_session)
    _add_turn(db_session, conv, intent="greet", sentiment="positive", topic="other")
    escalate, reason = should_escalate(db_session, conv)
    assert escalate is False
    assert reason is None


def test_notifier_default_is_console(db_session: Session) -> None:
    assert get_notifier("console").__class__.__name__ == "ConsoleNotifier"


def test_whatsapp_link_normalises_bare_10_digit_phone() -> None:
    assert _normalise_phone("98765 43210") == "919876543210"
    assert _normalise_phone(None) == ""


def test_whatsapp_notifier_builds_deep_link(db_session: Session) -> None:
    conv = _mk_conversation(db_session)
    esc = Escalation(
        raised_by_user_id=1,
        student_id=conv.student_id,
        reason="test",
        status="open",
        contact_phone="9876543210",
        channel="callback",
        priority="normal",
    )
    db_session.add(esc)
    db_session.commit()
    receipt = WhatsAppLinkNotifier().notify(esc)
    assert receipt["status"] == "link_created"
    assert receipt["link"] == "https://wa.me/919876543210"

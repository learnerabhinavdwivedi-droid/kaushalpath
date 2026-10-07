"""Human-escalation service (Phase 14).

Turns the old "insert a row" escalation into a real hand-off:

* ``build_case_pack``  - assemble everything a counsellor needs to pick up cold.
* ``auto_route``       - soft-assign to the student's least-loaded counsellor,
  otherwise leave the case in the shared pool (``assigned_counsellor_id`` NULL).
* ``should_escalate``  - decide whether a conversation needs a human now
  (resistance over threshold, an explicit request, or two unresolved concerns).
* ``create_escalation``- de-duplicate open cases, build the pack, route, persist
  and fire the notifier.
* ``claim_escalation`` - atomic claim so two counsellors cannot take one case.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.base import utcnow
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.human import CounsellorAssignment, Escalation
from app.models.occupation import Occupation
from app.models.recommendation import Recommendation
from app.models.student import Student
from app.services.conversation.grounder import ground_facts
from app.services.notifier import get_notifier
from app.services.resistance import calculate_shift_label

_OPEN_STATUSES = ("open", "assigned", "contacted")


def _latest_rs(db: Session, conversation_id: int) -> float | None:
    return db.scalar(
        select(ResistanceSnapshot.rs)
        .where(ResistanceSnapshot.conversation_id == conversation_id)
        .order_by(ResistanceSnapshot.turn_id.desc())
    )


def build_case_pack(db: Session, conversation: Conversation) -> dict[str, Any]:
    """Assemble the counsellor-facing case pack for a conversation.

    Includes the last 10 turns, the objection topics, the latest resistance
    score, the session shift label, the shortlisted trades (with their grounded
    facts) and the family context (district / state / income band / language).
    """
    turns = db.scalars(
        select(Turn)
        .where(Turn.conversation_id == conversation.id)
        .order_by(Turn.id.desc())
        .limit(10)
    ).all()
    turns = list(reversed(turns))

    all_turns = db.scalars(
        select(Turn).where(Turn.conversation_id == conversation.id).order_by(Turn.id)
    ).all()

    topics: list[str] = []
    for t in all_turns:
        if t.topic and t.topic not in topics:
            topics.append(t.topic)

    student = db.get(Student, conversation.student_id)

    shortlisted: list[dict[str, Any]] = []
    recs = db.scalars(
        select(Recommendation)
        .where(Recommendation.student_id == conversation.student_id)
        .order_by(Recommendation.rank.asc())
        .limit(3)
    ).all()
    for rec in recs:
        occ = db.get(Occupation, rec.occupation_id)
        facts = ground_facts(
            db, occupation_id=rec.occupation_id, student_id=conversation.student_id
        )
        shortlisted.append(
            {
                "occupation_id": rec.occupation_id,
                "name_en": occ.name_en if occ else str(rec.occupation_id),
                "rank": rec.rank,
                "score": rec.score,
                "facts": facts[:4],
            }
        )

    return {
        "conversation_id": conversation.id,
        "student_id": conversation.student_id,
        "language": conversation.lang,
        "family_context": {
            "district": student.district if student else None,
            "state": student.state if student else None,
            "income_band": student.income_band if student else None,
            "edu_level": student.edu_level if student else None,
            "language": student.language if student else conversation.lang,
        },
        "topics": topics,
        "latest_rs": _latest_rs(db, conversation.id),
        "shift": calculate_shift_label(list(all_turns)),
        "shortlisted_trades": shortlisted,
        "last_turns": [
            {
                "speaker": t.speaker,
                "text": t.text,
                "topic": t.topic,
                "sentiment": t.sentiment,
                "created_at": t.created_at.isoformat() if t.created_at else None,
            }
            for t in turns
        ],
    }


def auto_route(db: Session, student_id: int) -> int | None:
    """Pick the student's assigned counsellor with the lowest open load.

    Returns ``None`` when the student has no counsellor - the case then lands in
    the shared pool, visible to every counsellor (fixing the Phase 5/8 bug where
    unassigned cases were admin-only).
    """
    counsellor_ids = db.scalars(
        select(CounsellorAssignment.counsellor_id).where(
            CounsellorAssignment.student_id == student_id
        )
    ).all()
    if not counsellor_ids:
        return None

    best_id: int | None = None
    best_load: int | None = None
    for cid in counsellor_ids:
        open_count = len(
            db.scalars(
                select(Escalation.id).where(
                    Escalation.assigned_counsellor_id == cid,
                    Escalation.status.in_(_OPEN_STATUSES),
                )
            ).all()
        )
        if best_load is None or open_count < best_load:
            best_load = open_count
            best_id = cid
    return best_id


def has_open_duplicate(
    db: Session,
    student_id: int,
    reason: str,
    conversation_id: int | None = None,
    room_id: int | None = None,
) -> Escalation | None:
    """Return an existing still-open case for the same student + reason."""
    stmt = select(Escalation).where(
        Escalation.student_id == student_id,
        Escalation.reason == reason,
        Escalation.status.in_(_OPEN_STATUSES),
    )
    if conversation_id is not None:
        stmt = stmt.where(Escalation.conversation_id == conversation_id)
    if room_id is not None:
        stmt = stmt.where(Escalation.room_id == room_id)
    return db.scalars(stmt).first()


def should_escalate(db: Session, conversation: Conversation) -> tuple[bool, str | None]:
    """Decide whether a human is needed now. Returns ``(escalate, reason)``."""
    settings = get_settings()

    # 1. Explicit request to reach a human.
    asked = db.scalar(
        select(Turn.id).where(
            Turn.conversation_id == conversation.id,
            Turn.intent == "escalate",
        )
    )
    if asked is not None:
        return True, "explicit_request"

    # 2. Resistance over threshold.
    latest_rs = _latest_rs(db, conversation.id)
    if latest_rs is not None and latest_rs >= settings.escalation_rs_threshold:
        return True, "high_resistance"

    # 3. Two consecutive unresolved (concern/negative) family turns.
    recent = db.scalars(
        select(Turn)
        .where(
            Turn.conversation_id == conversation.id,
            Turn.speaker.in_(("learner", "parent")),
        )
        .order_by(Turn.id.desc())
        .limit(2)
    ).all()
    if len(recent) == 2 and all(
        (t.sentiment in ("negative", "concern")) for t in recent
    ):
        return True, "two_unresolved_turns"

    return False, None


def create_escalation(
    db: Session,
    *,
    student_id: int,
    raised_by_user_id: int,
    reason: str,
    occupation_id: int | None = None,
    conversation_id: int | None = None,
    room_id: int | None = None,
    contact_phone: str | None = None,
    preferred_language: str | None = None,
    preferred_slot: str | None = None,
    channel: str = "callback",
    priority: str = "normal",
    notify: bool = True,
) -> Escalation:
    """Create (or return the existing open) escalation, routed and notified."""
    existing = has_open_duplicate(db, student_id, reason, conversation_id, room_id)
    if existing:
        return existing

    if not preferred_language:
        student = db.get(Student, student_id)
        preferred_language = student.language if student else None

    esc = Escalation(
        room_id=room_id,
        conversation_id=conversation_id,
        raised_by_user_id=raised_by_user_id,
        student_id=student_id,
        occupation_id=occupation_id,
        reason=reason,
        status="open",
        contact_phone=contact_phone,
        preferred_language=preferred_language,
        preferred_slot=preferred_slot,
        channel=channel,
        priority=priority,
    )

    # Attach the case pack when the trigger is a conversation.
    if conversation_id is not None:
        conv = db.get(Conversation, conversation_id)
        if conv is not None:
            esc.case_pack_json = build_case_pack(db, conv)

    esc.assigned_counsellor_id = auto_route(db, student_id)
    # A matched counsellor means the case is routed to them immediately; a NULL
    # assignment leaves it status ``open`` in the shared pool for a claim.
    if esc.assigned_counsellor_id is not None:
        esc.mark("assigned")

    db.add(esc)
    db.commit()
    db.refresh(esc)

    if notify:
        get_notifier().notify(esc)
    return esc


def claim_escalation(db: Session, escalation_id: int, counsellor_id: int) -> Escalation | None:
    """Atomically claim an open case.

    Returns the claimed escalation, or ``None`` when the case was already taken
    (a single conditional UPDATE guarantees two counsellors cannot win).
    """
    result = db.execute(
        update(Escalation)
        .where(
            Escalation.id == escalation_id,
            Escalation.status == "open",
            Escalation.assigned_counsellor_id.is_(None),
        )
        .values(
            assigned_counsellor_id=counsellor_id,
            status="assigned",
            claimed_at=utcnow(),
        )
    )
    db.commit()
    if result.rowcount == 0:
        return None
    db.expire_all()
    return db.get(Escalation, escalation_id)

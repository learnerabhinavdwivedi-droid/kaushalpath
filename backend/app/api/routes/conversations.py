"""Conversational counselling routes (joint learner/parent turn-based engine)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Turn
from app.models.human import Escalation
from app.models.occupation import Occupation
from app.models.recommendation import Recommendation
from app.models.room import RoomMember
from app.models.student import Student
from app.models.user import User
from app.schemas.conversation import (
    ConversationCreate,
    ConversationOut,
    TurnCreate,
    TurnResponse,
)
from app.schemas.escalation import EscalationAck, EscalationCreate
from app.services.conversation import (
    classify_utterance,
    detect_language,
    generate_response,
    ground_facts,
)
from app.services.escalation_svc import create_escalation, should_escalate
from app.services.resistance import record_resistance_snapshot
from app.services.sentiment import analyze_sentiment

router = APIRouter(prefix="/conversations", tags=["conversations"])


def _check_conversation_access(conv: Conversation, user: User, db: Session) -> None:
    """Ensure caller has permission to view/interact with the conversation."""
    if user.role in ("counsellor", "admin"):
        return

    student = db.get(Student, conv.student_id)
    if student and student.user_id == user.id:
        return

    if conv.room_id is not None:
        member = db.scalar(
            select(RoomMember).where(
                RoomMember.room_id == conv.room_id, RoomMember.user_id == user.id
            )
        )
        if member:
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this conversation",
    )


@router.post("", response_model=ConversationOut, status_code=status.HTTP_201_CREATED)
def create_conversation(
    body: ConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Conversation:
    student = db.get(Student, body.student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    if current_user.role not in ("counsellor", "admin") and student.user_id != current_user.id:
        if body.room_id is not None:
            member = db.scalar(
                select(RoomMember).where(
                    RoomMember.room_id == body.room_id, RoomMember.user_id == current_user.id
                )
            )
            if not member:
                raise HTTPException(status_code=403, detail="Not authorized for this room")
        else:
            raise HTTPException(status_code=403, detail="Not authorized for this student")

    conv = Conversation(
        student_id=body.student_id,
        room_id=body.room_id,
        lang=body.lang or "hi",
        status="active",
    )
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


@router.get("/{conversation_id}", response_model=ConversationOut)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Conversation:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    _check_conversation_access(conv, current_user, db)
    return conv


@router.post("/{conversation_id}/turns", response_model=TurnResponse)
def add_turn(
    conversation_id: int,
    body: TurnCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> TurnResponse:
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    _check_conversation_access(conv, current_user, db)

    # A counsellor posting into the thread: store the human reply verbatim and
    # do NOT run the assistant pipeline (the family sees this in the same chat).
    if body.speaker == "counsellor" and current_user.role in ("counsellor", "admin"):
        reply_turn = Turn(
            conversation_id=conv.id,
            speaker="counsellor",
            text=body.text,
            lang=body.lang or conv.lang,
            intent="inform",
            topic=None,
            sentiment="neutral",
            intensity=0.0,
            facts_json=None,
            fallback_used=False,
        )
        db.add(reply_turn)
        db.commit()
        return TurnResponse(
            reply=body.text,
            lang=reply_turn.lang,
            intent="inform",
            topic="other",
            facts=[],
            followups=[],
            escalation_suggested=False,
            fallback_used=False,
        )

    # 1. Detect language
    lang = body.lang or detect_language(body.text)

    # 2. Intent and topic classification
    intent, topic, conf = classify_utterance(body.text)

    # 3. Sentiment & intensity analysis
    sentiment, intensity, _ = analyze_sentiment(body.text, lang=lang)
    if intent == "object" and sentiment == "neutral":
        sentiment = "negative"
        intensity = max(intensity, 0.4)
    elif intent == "greet" and sentiment == "neutral":
        sentiment = "positive"

    # 4. Determine occupation to ground facts against
    occ_id = body.occupation_ids[0] if body.occupation_ids else None
    if not occ_id:
        top_rec = db.scalar(
            select(Recommendation)
            .where(Recommendation.student_id == conv.student_id)
            .order_by(Recommendation.rank.asc())
        )
        if top_rec:
            occ_id = top_rec.occupation_id
        else:
            voc_occ = db.scalar(
                select(Occupation).where(Occupation.is_vocational.is_(True)).order_by(Occupation.id.asc())
            )
            occ_id = voc_occ.id if voc_occ else 1

    # 5. Fetch grounded facts via OutcomeService
    facts = ground_facts(
        db=db,
        occupation_id=occ_id,
        student_id=conv.student_id,
    )

    if body.occupation_ids:
        occs = db.query(Occupation).filter(Occupation.id.in_(body.occupation_ids)).all()
        if occs:
            facts.append({"key": "comparing_careers", "value": ", ".join(occ.title for occ in occs)})

    state = conv.state_json if getattr(conv, 'state_json', None) is not None else {}
    if not isinstance(state, dict):
        state = {}
    prev_reply = state.get("last_reply")
    turn_count = state.get("turn_count", 0)

    reversed_turns = db.query(Turn).filter(Turn.conversation_id == conv.id).order_by(Turn.id.desc()).limit(6).all()
    reversed_turns.reverse()
    history = [{"speaker": t.speaker, "text": t.text} for t in reversed_turns]

    # 6. Generate grounded response with hallucination validation
    res = generate_response(
        topic=topic, 
        lang=lang, 
        facts=facts, 
        history=history, 
        prev_reply=prev_reply, 
        turn_count=turn_count
    )

    # 7. Persist turns
    user_turn = Turn(
        conversation_id=conv.id,
        speaker=body.speaker,
        text=body.text,
        lang=lang,
        intent=intent,
        topic=topic,
        sentiment=sentiment,
        intensity=intensity,
        facts_json=None,
        fallback_used=False,
    )
    db.add(user_turn)
    db.flush()

    # Record Rs snapshot
    record_resistance_snapshot(conversation=conv, turn=user_turn, db=db)

    asst_turn = Turn(
        conversation_id=conv.id,
        speaker="assistant",
        text=res["reply"],
        lang=lang,
        intent="inform",
        topic=topic,
        sentiment="neutral",
        intensity=0.0,
        facts_json=facts,
        fallback_used=res["fallback_used"],
    )
    db.add(asst_turn)

    state["last_reply"] = res["reply"]
    state["turn_count"] = turn_count + 1
    conv.state_json = state
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(conv, "state_json")

    # 8. Auto-escalation decision (Phase 14 service): explicit request, Rs over the
    #    threshold, or two consecutive unresolved family turns. This only nudges the
    #    family toward the escalate sheet; the record itself is created on consent.
    escalation_suggested, _ = should_escalate(db, conv)
    if intent == "escalate":
        conv.status = "escalated"

    db.commit()

    return TurnResponse(
        reply=res["reply"],
        lang=lang,
        intent=intent,
        topic=topic,
        facts=facts,
        followups=res["followups"],
        escalation_suggested=escalation_suggested,
        fallback_used=res["fallback_used"],
    )


@router.get("/{conversation_id}/escalation", response_model=EscalationAck)
def get_conversation_escalation(
    conversation_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EscalationAck:
    """Latest hand-off case for this conversation, for the family-facing
    live-status chip polled by the Phase 15 chat UI. Deliberately returns
    only lifecycle fields — no notes or case pack (counsellor-private)."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    _check_conversation_access(conv, current_user, db)

    esc = db.scalar(
        select(Escalation)
        .where(Escalation.conversation_id == conv.id)
        .order_by(Escalation.id.desc())
    )
    if not esc:
        raise HTTPException(status_code=404, detail="No escalation for this conversation")
    return EscalationAck(
        id=esc.id,
        status=esc.status,
        assigned_counsellor_id=esc.assigned_counsellor_id,
        in_pool=esc.assigned_counsellor_id is None,
        case_pack=None,
    )


@router.post(
    "/{conversation_id}/escalate",
    response_model=EscalationAck,
    status_code=status.HTTP_201_CREATED,
)
def escalate_conversation(
    conversation_id: int,
    body: EscalationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> EscalationAck:
    """Raise a live-counsellor hand-off from a conversation (Phase 14).

    Builds a case pack, soft-routes to the student's least-loaded counsellor
    (else the shared pool), fires the notifier, and marks the conversation
    ``escalated``.
    """
    conv = db.get(Conversation, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    _check_conversation_access(conv, current_user, db)

    esc = create_escalation(
        db,
        student_id=conv.student_id,
        raised_by_user_id=current_user.id,
        reason=body.reason,
        occupation_id=body.occupation_id,
        conversation_id=conv.id,
        room_id=conv.room_id,
        contact_phone=body.contact_phone,
        preferred_language=body.preferred_language or conv.lang,
        preferred_slot=body.preferred_slot,
        channel=body.channel,
        priority=body.priority,
    )

    if conv.status == "active":
        conv.status = "escalated"
        db.commit()

    return EscalationAck(
        id=esc.id,
        status=esc.status,
        assigned_counsellor_id=esc.assigned_counsellor_id,
        in_pool=esc.assigned_counsellor_id is None,
        case_pack=esc.case_pack_json,
    )

"""Conversational counselling routes (joint learner/parent turn-based engine)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.conversation import Conversation, Turn
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
from app.services.conversation import (
    classify_utterance,
    detect_language,
    generate_response,
    ground_facts,
)

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

    # 1. Detect language
    lang = body.lang or detect_language(body.text)

    # 2. Intent and topic classification
    intent, topic, conf = classify_utterance(body.text)

    # 3. Sentiment derivation
    if intent == "object":
        sentiment = "concern"
    elif intent == "greet":
        sentiment = "positive"
    else:
        sentiment = "neutral"

    # 4. Determine occupation to ground facts against
    occ_id = body.occupation_id
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

    # 6. Generate grounded response with hallucination validation
    res = generate_response(topic=topic, lang=lang, facts=facts)

    # 7. Persist turns
    user_turn = Turn(
        conversation_id=conv.id,
        speaker=body.speaker,
        text=body.text,
        lang=lang,
        intent=intent,
        topic=topic,
        sentiment=sentiment,
        facts_json=None,
        fallback_used=False,
    )
    db.add(user_turn)

    asst_turn = Turn(
        conversation_id=conv.id,
        speaker="assistant",
        text=res["reply"],
        lang=lang,
        intent="inform",
        topic=topic,
        sentiment="neutral",
        facts_json=facts,
        fallback_used=res["fallback_used"],
    )
    db.add(asst_turn)

    # 8. Check escalation heuristics
    prior_concerns = db.scalar(
        select(Turn)
        .where(Turn.conversation_id == conv.id, Turn.sentiment == "concern")
    )
    escalation_suggested = (intent == "escalate") or (sentiment == "concern" and prior_concerns is not None)
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

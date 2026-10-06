"""Resistance score calculation, snapshotting, and session sentiment shift tracking."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.conversation import Conversation, ResistanceSnapshot, Turn
from app.models.vote import Vote


def calculate_consensus_delta(conversation: Conversation, db: Session) -> float:
    """Calculate consensus delta in [0.0, 1.0] from room votes and parent turns."""
    delta = 0.0

    # 1. Check parent turns in this conversation
    parent_turns = db.scalars(
        select(Turn)
        .where(Turn.conversation_id == conversation.id, Turn.speaker == "parent")
    ).all()

    if parent_turns:
        pos_count = sum(1 for t in parent_turns if t.sentiment == "positive")
        neg_count = sum(1 for t in parent_turns if t.sentiment == "negative")
        # Ratio of positive vs negative parental participation
        parent_ratio = pos_count / len(parent_turns)
        delta += parent_ratio * 0.5
        if neg_count == 0 and pos_count > 0:
            delta += 0.2

    # 2. Check room votes if linked to a room
    if conversation.room_id is not None:
        votes = db.scalars(
            select(Vote).where(Vote.room_id == conversation.room_id)
        ).all()
        if votes:
            scores = [v.score for v in votes]
            # Higher average score and lower variance indicate higher consensus
            avg_score = sum(scores) / len(scores)
            norm_score = max(0.0, min(1.0, (avg_score - 1.0) / 4.0))
            delta += norm_score * 0.5

    return min(1.0, max(0.0, delta))


def compute_resistance_score(
    topic: str,
    sentiment: str,
    intensity: float,
    conversation: Conversation,
    db: Session,
) -> float:
    """Compute resistance score rs in [0.0, 1.0]:

    rs = w1 * topic_weight + w2 * intensity - w3 * consensus_delta
    """
    settings = get_settings()
    w1 = settings.resistance_w_topic
    w2 = settings.resistance_w_intensity
    w3 = settings.resistance_w_consensus
    topic_weight = settings.resistance_topic_weights.get(topic, 0.30)

    consensus_delta = calculate_consensus_delta(conversation, db)

    if sentiment == "positive":
        raw_rs = max(0.0, 0.15 - (0.3 * consensus_delta))
    elif sentiment == "negative":
        raw_rs = (w1 * topic_weight) + (w2 * intensity) - (w3 * consensus_delta)
    else:  # neutral
        raw_rs = (0.5 * w1 * topic_weight) + (0.3 * intensity) - (w3 * consensus_delta)

    return round(min(1.0, max(0.0, raw_rs)), 3)


def record_resistance_snapshot(
    conversation: Conversation,
    turn: Turn,
    db: Session,
) -> ResistanceSnapshot:
    """Compute and persist an Rs snapshot for the turn."""
    rs = compute_resistance_score(
        topic=turn.topic or "other",
        sentiment=turn.sentiment or "neutral",
        intensity=turn.intensity or 0.0,
        conversation=conversation,
        db=db,
    )
    snapshot = ResistanceSnapshot(
        conversation_id=conversation.id,
        turn_id=turn.id,
        rs=rs,
    )
    db.add(snapshot)
    return snapshot


def calculate_shift_label(turns: list[Turn]) -> str:
    """Determine conversation shift label: 'softened' | 'hardened' | 'unchanged'.

    Compares mean sentiment of first third vs last third of turns.
    """
    if len(turns) < 3:
        return "unchanged"

    def _val(s: str | None) -> float:
        if s == "positive":
            return 1.0
        elif s == "negative":
            return -1.0
        return 0.0

    k = max(1, len(turns) // 3)
    first_third = turns[:k]
    last_third = turns[-k:]

    mean_start = sum(_val(t.sentiment) for t in first_third) / len(first_third)
    mean_end = sum(_val(t.sentiment) for t in last_third) / len(last_third)
    diff = mean_end - mean_start

    if diff >= 0.35:
        return "softened"
    elif diff <= -0.35:
        return "hardened"
    return "unchanged"

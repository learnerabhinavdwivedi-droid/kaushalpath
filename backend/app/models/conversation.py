"""Conversation and Turn models for joint learner/parent conversational counselling."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

CONVERSATION_STATUSES = ("active", "escalated", "closed")
TURN_SPEAKERS = ("learner", "parent", "counsellor", "assistant")
CONVERSATION_TOPICS = ("income", "security", "social", "safety", "distance", "cost", "other")


class Conversation(Base, TimestampMixin):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=True
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    lang: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)

    turns: Mapped[list[Turn]] = relationship(
        "Turn", back_populates="conversation", cascade="all, delete-orphan", order_by="Turn.id"
    )


class Turn(Base, TimestampMixin):
    __tablename__ = "turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    speaker: Mapped[str] = mapped_column(String(16), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    lang: Mapped[str] = mapped_column(String(10), default="hi", nullable=False)
    intent: Mapped[str | None] = mapped_column(String(32), nullable=True)
    topic: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    facts_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    fallback_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="turns")

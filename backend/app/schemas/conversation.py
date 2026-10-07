"""Schemas for conversational engine (turns, conversations, grounded facts)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    student_id: int
    room_id: int | None = None
    lang: str = "hi"


class TurnCreate(BaseModel):
    speaker: str = Field(default="learner", description="learner | parent | counsellor")
    text: str = Field(..., min_length=1)
    occupation_ids: list[int] = []
    lang: str | None = None


class TurnResponse(BaseModel):
    reply: str
    lang: str
    intent: str
    topic: str
    facts: list[dict[str, Any]]
    followups: list[str]
    escalation_suggested: bool
    fallback_used: bool


class TurnOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    speaker: str
    text: str
    lang: str
    intent: str | None = None
    topic: str | None = None
    sentiment: str | None = None
    intensity: float = 0.0
    facts_json: list[dict[str, Any]] | None = None
    fallback_used: bool = False
    created_at: datetime


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    room_id: int | None = None
    lang: str
    status: str
    created_at: datetime
    turns: list[TurnOut] = []


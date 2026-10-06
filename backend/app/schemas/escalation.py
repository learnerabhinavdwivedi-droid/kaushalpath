"""Schemas for Phase 14 human escalation (hand-off, case pack, lifecycle)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.human import ESCALATION_CHANNELS, ESCALATION_PRIORITIES


class EscalationCreate(BaseModel):
    """Body for raising a hand-off from a conversation."""

    reason: str = Field(min_length=1)
    occupation_id: int | None = None
    contact_phone: str | None = None
    preferred_language: str | None = None
    preferred_slot: str | None = None
    channel: str = Field(default="callback")
    priority: str = Field(default="normal")

    @field_validator("channel")
    @classmethod
    def _channel_known(cls, v: str) -> str:
        if v not in ESCALATION_CHANNELS:
            raise ValueError(f"channel must be one of {ESCALATION_CHANNELS}")
        return v

    @field_validator("priority")
    @classmethod
    def _priority_known(cls, v: str) -> str:
        if v not in ESCALATION_PRIORITIES:
            raise ValueError(f"priority must be one of {ESCALATION_PRIORITIES}")
        return v


class EscalationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    room_id: int | None = None
    conversation_id: int | None = None
    student_id: int
    occupation_id: int | None = None
    reason: str
    status: str
    assigned_counsellor_id: int | None = None
    channel: str
    priority: str
    preferred_language: str | None = None
    preferred_slot: str | None = None
    notes: str | None = None
    claimed_at: datetime | None = None
    contacted_at: datetime | None = None
    resolved_at: datetime | None = None
    created_at: datetime


class EscalationAck(BaseModel):
    """Lightweight response after creating / transitioning a case."""

    id: int
    status: str
    assigned_counsellor_id: int | None = None
    in_pool: bool
    case_pack: dict[str, Any] | None = None


class CasePackTurn(BaseModel):
    speaker: str
    text: str
    topic: str | None = None
    sentiment: str | None = None
    created_at: datetime


class CasePack(BaseModel):
    """Everything a counsellor needs to pick up the case cold."""

    conversation_id: int | None = None
    student_id: int
    language: str | None = None
    family_context: dict[str, Any] = {}
    topics: list[str] = []
    latest_rs: float | None = None
    shift: str | None = None
    shortlisted_trades: list[dict[str, Any]] = []
    last_turns: list[CasePackTurn] = []

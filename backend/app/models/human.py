"""Human-in-the-loop tables (PS 26241 official).

Three concerns live here, kept as plain transactional tables (no `SourceMixin` —
that provenance contract is only for reference/catalogue data):

* ``Escalation`` — a student/parent raises it on a room when the AI can't resolve
  a concern; a counsellor works it out of a queue.
* ``Objection`` — a parental objection raised in the room's conversation surface,
  tagged with a topic + sentiment; feeds the Phase 8 resistance dashboard.
* ``CounsellorAssignment`` — which counsellor owns which student; the source of
  the counsellor "cohort" (only assigned students are visible).
* ``CounsellorOverride`` — an audit-logged manual recommendation a counsellor
  records on top of the model output.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utcnow

ESCALATION_STATUSES = ("open", "assigned", "contacted", "resolved", "unreachable")
# Channel the counsellor should reach the family on, and the handling priority.
ESCALATION_CHANNELS = ("callback", "chat", "visit")
ESCALATION_PRIORITIES = ("low", "normal", "high")
# Conversational objection topics (PS 26241 parental concerns) and the
# sentiment we tag each parent interaction with (feeds Phase 8 dashboard).
OBJECTION_TOPICS = ("income", "security", "social", "safety", "distance", "cost", "other")
OBJECTION_SENTIMENTS = ("concern", "neutral", "positive")


class Escalation(Base, TimestampMixin):
    """A request for a live human counsellor (Phase 14).

    Raised from a conversation (``conversation_id``) or a family room
    (``room_id``); both are nullable so a case can be either conversation- or
    room-scoped. The status lifecycle is
    ``open -> assigned -> contacted -> resolved`` (with ``unreachable`` for
    dead-ends). A resolved case never blocks a fresh one, so there is no
    database-level uniqueness on the reason any more -- de-duplication of still
    -open cases is enforced in ``escalation_svc``.
    """

    __tablename__ = "escalations"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int | None] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=True
    )
    conversation_id: Mapped[int | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True, nullable=True
    )
    raised_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[int | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")
    assigned_counsellor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # Phase 14 hand-off fields.
    contact_phone: Mapped[str | None] = mapped_column(String(24), nullable=True)
    preferred_language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    preferred_slot: Mapped[str | None] = mapped_column(String(40), nullable=True)
    channel: Mapped[str] = mapped_column(String(10), nullable=False, default="callback")
    priority: Mapped[str] = mapped_column(String(8), nullable=False, default="normal")
    case_pack_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contacted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def mark(self, status: str) -> None:
        """Transition the lifecycle and stamp the matching timestamp."""
        self.status = status
        if status == "assigned":
            self.claimed_at = utcnow()
        elif status == "contacted":
            self.contacted_at = utcnow()
        elif status == "resolved":
            self.resolved_at = utcnow()


class CounsellorAssignment(Base, TimestampMixin):
    __tablename__ = "counsellor_assignments"
    __table_args__ = (
        UniqueConstraint("counsellor_id", "student_id", name="uq_counsellor_assignment"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    counsellor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )


class Objection(Base, TimestampMixin):
    """A parental objection raised in a room, tagged with a topic + sentiment.

    Recorded from the deterministic conversation surface (the LLM only
    verbalises the ranked template answer, never decides). Aggregated later by
    the Phase 8 admin resistance dashboard.
    """

    __tablename__ = "objections"

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    raised_by_user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[int | None] = mapped_column(
        ForeignKey("occupations.id", ondelete="SET NULL"), index=True, nullable=True
    )
    topic: Mapped[str] = mapped_column(String(16), nullable=False, default="other")
    sentiment: Mapped[str] = mapped_column(String(12), nullable=False, default="concern")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class CounsellorOverride(Base, TimestampMixin):
    """Audit trail for a counsellor overriding the model's recommendation."""

    __tablename__ = "counsellor_overrides"

    id: Mapped[int] = mapped_column(primary_key=True)
    counsellor_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    note: Mapped[str] = mapped_column(Text, nullable=False)

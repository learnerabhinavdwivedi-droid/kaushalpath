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

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ESCALATION_STATUSES = ("open", "resolved")
# Conversational objection topics (PS 26241 parental concerns) and the
# sentiment we tag each parent interaction with (feeds Phase 8 dashboard).
OBJECTION_TOPICS = ("income", "security", "social", "safety", "distance", "cost", "other")
OBJECTION_SENTIMENTS = ("concern", "neutral", "positive")


class Escalation(Base, TimestampMixin):
    __tablename__ = "escalations"
    __table_args__ = (
        UniqueConstraint("room_id", "raised_by_user_id", "reason", name="uq_escalation"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False
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
    status: Mapped[str] = mapped_column(String(12), nullable=False, default="open")
    assigned_counsellor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )


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

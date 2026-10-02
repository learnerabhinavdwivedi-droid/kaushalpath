"""Family Decision Room, membership and per-member criteria weights."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, utcnow


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(12), unique=True, index=True, nullable=False)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    created_at_dt: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class RoomMember(Base, TimestampMixin):
    __tablename__ = "room_members"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_room_member"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="parent")


class CriteriaWeight(Base, TimestampMixin):
    """Per-member weights over the 5 criteria; normalised in the service layer."""

    __tablename__ = "criteria_weights"
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_criteria_weights"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cost: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    duration: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    salary: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    local_jobs: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)
    distance: Mapped[float] = mapped_column(Float, default=0.2, nullable=False)

"""Progression pathways from courses (NSQF level-up, lateral entry, etc.)."""
from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SourceMixin, TimestampMixin


class ProgressionPath(Base, TimestampMixin, SourceMixin):
    __tablename__ = "progression_paths"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    to_label: Mapped[str] = mapped_column(String(200), nullable=False)
    to_course_id: Mapped[int | None] = mapped_column(
        ForeignKey("courses.id", ondelete="SET NULL"), nullable=True
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    credit_note: Mapped[str | None] = mapped_column(String(255), nullable=True)

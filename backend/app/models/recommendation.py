"""Stored recommendation with explainable reason codes."""
from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # >=2 reason codes + data source per RULES (no black box).
    reasons_json: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

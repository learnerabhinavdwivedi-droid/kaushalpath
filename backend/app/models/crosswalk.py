"""System-to-system occupation / trade crosswalks (Phase 19 Data Foundation)."""
from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Crosswalk(Base, TimestampMixin):
    __tablename__ = "crosswalk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_system: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    from_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    to_system: Mapped[str] = mapped_column(String(32), index=True, nullable=False)
    to_code: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    relation: Mapped[str] = mapped_column(
        String(16),
        CheckConstraint("relation IN ('exact', 'broad', 'narrow', 'close')"),
        nullable=False,
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(
        String(32),
        CheckConstraint("method IN ('official', 'name_match', 'manual')"),
        nullable=False,
    )
    needs_review: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

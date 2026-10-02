"""Assessment result snapshot (RIASEC + aptitude + confidence)."""
from __future__ import annotations

from sqlalchemy import JSON, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Assessment(Base, TimestampMixin):
    __tablename__ = "assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(
        ForeignKey("students.id", ondelete="CASCADE"), index=True, nullable=False
    )
    items_answered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    riasec_r: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_i: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_a: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_s: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_e: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_c: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    apt_num: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    apt_verbal: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    apt_spatial: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    apt_mech: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    confidence: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Resumable adaptive-session snapshot (see ml/assessment/adaptive.new_state).
    # `status` is denormalised out of the state for cheap querying/indexing.
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    state_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

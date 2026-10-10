"""Provider outcomes for specific trade + centre + cohort."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EvidenceMixin, SourceMixin, TimestampMixin


class ProviderOutcome(Base, TimestampMixin, SourceMixin, EvidenceMixin):
    __tablename__ = "provider_outcomes"

    id: Mapped[int] = mapped_column(primary_key=True)
    provider_id: Mapped[int] = mapped_column(
        ForeignKey("centres.id", ondelete="CASCADE"), index=True, nullable=False
    )
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    cohort_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    enrolled: Mapped[int | None] = mapped_column(Integer, nullable=True)
    certified: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    placement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    earnings_p25: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings_median: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings_p75: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    self_employed_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    apprenticeship_stipend_inr: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)

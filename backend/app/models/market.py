"""Market signals (salary / demand / placement) per occupation + state."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, EvidenceMixin, SourceMixin, TimestampMixin


class Market(Base, TimestampMixin, SourceMixin, EvidenceMixin):
    __tablename__ = "market"

    id: Mapped[int] = mapped_column(primary_key=True)
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    state: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    district: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    avg_salary_inr: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings_p25: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    earnings_p75: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    demand_index: Mapped[float | None] = mapped_column(Float, nullable=True)
    placement_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)

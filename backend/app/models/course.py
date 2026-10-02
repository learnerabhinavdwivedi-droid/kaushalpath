"""Course / training programme leading to an occupation."""
from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SourceMixin, TimestampMixin


class Course(Base, TimestampMixin, SourceMixin):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True)
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    nsqf_level: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)
    min_edu: Mapped[str | None] = mapped_column(String(20), nullable=True)
    fee_inr: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    cert_body: Mapped[str | None] = mapped_column(String(200), nullable=True)

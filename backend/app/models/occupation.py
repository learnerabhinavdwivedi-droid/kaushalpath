"""Occupation master (RIASEC profile + taxonomy codes)."""
from __future__ import annotations

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SourceMixin, TimestampMixin


class Occupation(Base, TimestampMixin, SourceMixin):
    __tablename__ = "occupations"

    id: Mapped[int] = mapped_column(primary_key=True)
    name_en: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    name_hi: Mapped[str | None] = mapped_column(String(200), nullable=True)
    nco_code: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    onet_code: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    esco_uri: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nsqf_level: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Holland RIASEC scores (0-10 scale).
    riasec_r: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_i: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_a: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_s: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_e: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    riasec_c: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

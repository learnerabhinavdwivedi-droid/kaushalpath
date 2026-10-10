"""Canonical LGD Geography hierarchy and aliases (Phase 19 Data Foundation)."""
from __future__ import annotations

from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Geo(Base, TimestampMixin):
    __tablename__ = "geo"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    lgd_state_code: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    lgd_district_code: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    state: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    district: Mapped[str] = mapped_column(String(120), index=True, nullable=False)

    __table_args__ = (
        UniqueConstraint("lgd_state_code", "lgd_district_code", name="uq_geo_state_district"),
    )


class GeoAlias(Base, TimestampMixin):
    __tablename__ = "geo_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alias: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    code: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    # kind: 'state' or 'district'
    kind: Mapped[str] = mapped_column(String(16), default="district", nullable=False)


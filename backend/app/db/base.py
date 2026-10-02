"""Declarative Base + shared mixins.

`SourceMixin` enforces the RULES.md provenance contract on reference-data
tables: every row carries `source`, `source_year` and `is_demo` so demo data
can never be presented as real.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""


def utcnow() -> datetime:
    return datetime.now(UTC)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SourceMixin:
    """Provenance fields required on every reference-data row."""

    source: Mapped[str] = mapped_column(String(120), nullable=False)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_demo: Mapped[bool] = mapped_column(default=True, nullable=False)
    needs_review: Mapped[bool] = mapped_column(default=False, nullable=False)

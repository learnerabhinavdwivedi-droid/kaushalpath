"""Declarative Base + shared mixins.

`SourceMixin` enforces the RULES.md provenance contract on reference-data
tables: every row carries `source`, `source_year` and `is_demo` so demo data
can never be presented as real.
"""
from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String, Text, func
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


class EvidenceMixin:
    """Phase 19 evidence policy fields."""

    evidence_grade: Mapped[str] = mapped_column(
        String(1),
        CheckConstraint("evidence_grade IN ('A', 'B', 'C', 'D')"),
        default="D",
        server_default="D",
        nullable=False,
    )
    n: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    retrieved_on: Mapped[str | None] = mapped_column(String(32), nullable=True)
    metric_definition: Mapped[str | None] = mapped_column(Text, nullable=True)


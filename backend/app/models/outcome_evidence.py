"""Unified Outcome Evidence Model (Phase 22 - Outcome Evidence Engine).

Stores empirical outcome signals from DGT STRIVE tracer studies, PMKVY,
DGT ITI scorecards, PLFS aggregates, and PS-provided datasets with explicit
grain, definitions, sample sizes, and empirical Bayes confidence intervals.
"""
from __future__ import annotations

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base


class OutcomeEvidence(Base):
    __tablename__ = "outcome_evidence"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("occupations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Geographic grain: 'provider' | 'district' | 'state' | 'national'
    geo_level: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    # LGD code for state / district (from Phase 19 Geo Registry)
    lgd_code: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    state: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    district: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Provider / centre foreign key if geo_level == 'provider'
    provider_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("centres.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Reporting period
    period_start: Mapped[str | None] = mapped_column(String(32), nullable=True)
    period_end: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Metric type: placement_rate | earnings_monthly_inr | self_employed_pct |
    # apprenticeship_stipend_inr | pass_rate | admission_rate
    metric: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Numerical value
    value: Mapped[float] = mapped_column(Float, nullable=False)

    # Value shape: rate | mean | median | band | p25 | p75
    value_shape: Mapped[str] = mapped_column(String(32), nullable=False)

    # Sample size (n)
    n: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Definition: reported | verified | survey
    definition: Mapped[str] = mapped_column(String(32), nullable=False)

    # Scheme version: '1.0' | '2.0' | '3.0' | None
    scheme_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Source reference (from SOURCES.yaml)
    source_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # Evidence grade: A | B | C | D
    evidence_grade: Mapped[str] = mapped_column(String(8), nullable=False, index=True)

    # Empirical Bayes 80% credible interval
    ci_low: Mapped[float | None] = mapped_column(Float, nullable=True)
    ci_high: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Audit & provenance fields (Data Addendum Rule 1)
    page_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str] = mapped_column(String(256), nullable=False)
    source_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retrieved_on: Mapped[str] = mapped_column(String(32), nullable=False)
    licence: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="Open Government Data (OGD) India",
        server_default="Open Government Data (OGD) India",
    )
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    occupation = relationship("Occupation", backref="outcome_evidence_rows")
    centre = relationship("Centre", backref="outcome_evidence_rows")

    @validates("definition")
    def validate_definition(self, key: str, value: str) -> str:
        allowed = {"official", "survey", "verified", "reported"}
        if value not in allowed:
            raise ValueError(f"definition must be one of {allowed}, got '{value}'")
        return value

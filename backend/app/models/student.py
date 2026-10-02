"""Student profile + hard constraints (fed to the eligibility filters in Phase 3)."""
from __future__ import annotations

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

EDU_LEVELS = ("8th", "10th", "12th", "ITI", "diploma", "graduate")
BUDGET_BANDS = ("low", "mid", "high")
# Household-income bracket — PS 26241 tailors output to the family's income
# context. Kept coarse + nullable so it is always optional at intake.
INCOME_BANDS = ("lt_1l", "1l_3l", "3l_6l", "gt_6l")


class Student(Base, TimestampMixin):
    __tablename__ = "students"
    __table_args__ = (
        CheckConstraint(f"edu_level IN {EDU_LEVELS}", name="ck_student_edu"),
        CheckConstraint(f"budget_band IN {BUDGET_BANDS}", name="ck_student_budget"),
        CheckConstraint(f"income_band IN {INCOME_BANDS}", name="ck_student_income"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True, index=True
    )
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    edu_level: Mapped[str] = mapped_column(String(20), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    budget_band: Mapped[str] = mapped_column(String(10), nullable=False, default="mid")
    income_band: Mapped[str | None] = mapped_column(String(10), nullable=True)
    relocate_ok: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="hi")
    max_duration_months: Mapped[int | None] = mapped_column(Integer, nullable=True)

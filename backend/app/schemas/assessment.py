"""Assessment API contracts (PHASE_2.md).

Request/response models for the adaptive RIASEC + aptitude flow: intake
constraints, the next-item envelope, an answer, and the resulting profile.
These mirror the plain-dict session state produced by `ml/assessment/adaptive`.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.student import BUDGET_BANDS, EDU_LEVELS, INCOME_BANDS


class ConstraintsIn(BaseModel):
    """Hard-constraint intake (feeds the Phase 3 eligibility filters).

    `income_band` is the household-income bracket the PS calls for; it shapes
    the family-facing explanation, never the interest/aptitude score.
    """

    age: int | None = None
    edu_level: str
    district: str
    state: str
    budget_band: str = "mid"
    income_band: str | None = None
    relocate_ok: bool = False
    language: str = "hi"
    max_duration_months: int | None = None

    @field_validator("edu_level")
    @classmethod
    def _edu(cls, v: str) -> str:
        if v not in EDU_LEVELS:
            raise ValueError(f"edu_level must be one of {list(EDU_LEVELS)}")
        return v

    @field_validator("budget_band")
    @classmethod
    def _budget(cls, v: str) -> str:
        if v not in BUDGET_BANDS:
            raise ValueError(f"budget_band must be one of {list(BUDGET_BANDS)}")
        return v

    @field_validator("income_band")
    @classmethod
    def _income(cls, v: str | None) -> str | None:
        if v is not None and v not in INCOME_BANDS:
            raise ValueError(f"income_band must be one of {list(INCOME_BANDS)}")
        return v


class InterestItemOut(BaseModel):
    id: str
    section: str = "interest"
    text: str
    scale: list[int] = Field(default_factory=lambda: [1, 2, 3, 4, 5])


class AptitudeItemOut(BaseModel):
    id: str
    section: str = "aptitude"
    dimension: str
    text: str
    options: list[str]


class NextItemOut(BaseModel):
    """The item to show, or a bare progress packet when the session is done."""

    assessment_id: int
    status: str
    done: bool
    items_answered: int
    confidence: float
    item: InterestItemOut | AptitudeItemOut | None = None


class AnswerIn(BaseModel):
    """An answer to the currently-served item.

    `assessment_id` targets the open session (echoed back from /next).
    `item_id` is optional: when supplied the server rejects a mismatch (guards
    against answering a stale item after a concurrent request). Interest answers
    are 1..5; aptitude answers are one of the item's option strings.
    """

    assessment_id: int
    answer: Any
    item_id: str | None = None


class AssessmentResult(BaseModel):
    riasec: dict[str, float]
    top3_code: str
    aptitude: dict[str, float]
    confidence: float
    items_answered: int
    status: str


class ProfileOut(AssessmentResult):
    assessment_id: int
    student_id: int


class MessageOut(BaseModel):
    detail: str

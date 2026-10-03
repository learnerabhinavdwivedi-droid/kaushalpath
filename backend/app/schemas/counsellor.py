"""Phase 8: counsellor-dashboard, feedback and audit schemas.

Kept explicit (no bare ``dict`` responses) so the OpenAPI contract documents
what the dashboard renders. Aggregated views only ever carry bucket counts —
never individual student rows (PHASE_8: hide groups smaller than 5).
"""
from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.models.feedback import FEEDBACK_SENTIMENTS, FEEDBACK_TOPICS


class CohortFilters(BaseModel):
    """Optional query filters for the cohort list."""

    district: str | None = None
    edu_level: str | None = None
    language: str | None = None
    status: str | None = Field(default=None, pattern="^(assessed|pending_assessment)$")


class CohortRow(BaseModel):
    student_id: int
    district: str
    edu_level: str
    language: str
    status: str
    has_room: bool
    open_escalations: int


class RecommendationRow(BaseModel):
    occupation_id: int
    occupation_name: str
    rank: int
    score: float
    reasons: list[dict]
    is_demo: bool


class RoomStatusOut(BaseModel):
    code: str | None
    members: int
    votes: int
    objections: int
    consensus_reached: bool


class StudentDetailOut(BaseModel):
    student_id: int
    district: str
    state: str
    edu_level: str
    language: str
    budget_band: str
    assessment: dict | None
    recommendations: list[RecommendationRow]
    overrides: list[dict]
    room: RoomStatusOut | None


class FeedbackCreate(BaseModel):
    recommendation_id: int = Field(ge=1)
    helpful: bool = False
    chosen: bool = False
    topic: str = Field(default="none")
    sentiment: str = Field(default="none")

    @field_validator("topic")
    @classmethod
    def _topic_known(cls, v: str) -> str:
        if v not in FEEDBACK_TOPICS:
            raise ValueError(f"topic must be one of {FEEDBACK_TOPICS}")
        return v

    @field_validator("sentiment")
    @classmethod
    def _sentiment_known(cls, v: str) -> str:
        if v not in FEEDBACK_SENTIMENTS:
            raise ValueError(f"sentiment must be one of {FEEDBACK_SENTIMENTS}")
        return v


class FeedbackOut(BaseModel):
    id: int
    recommendation_id: int
    helpful: bool
    chosen: bool
    topic: str
    sentiment: str


class AuditEntryOut(BaseModel):
    id: int
    actor_user_id: int | None
    action: str
    entity_type: str
    entity_id: str | None
    detail: dict | None
    created_at: str | None


class CountBucket(BaseModel):
    label: str
    count: int


class TradeBucket(BaseModel):
    occupation: str
    count: int


class DistrictBucket(BaseModel):
    district: str
    n_students: int
    top_trade: str
    recommendations: int


class ResistanceOut(BaseModel):
    total_objections: int
    by_topic: list[CountBucket]
    by_district: list[CountBucket]
    by_trade: list[CountBucket]
    concern_by_topic: list[CountBucket]
    suppressed_groups: int


class AnalyticsOut(BaseModel):
    riasec: dict
    top_trades: dict
    dropoff: dict
    rooms: dict
    avg_items: dict
    district_mismatch: dict

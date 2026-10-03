"""Feedback on a recommendation (helpful / chosen + sentiment tag) — feeds the
retraining loop. The topic/sentiment pair reuses the Phase 7 objection taxonomy
so the resistance dashboard (Phase 8) aggregates one consistent vocabulary."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin
from app.models.human import OBJECTION_SENTIMENTS, OBJECTION_TOPICS

# "none" extends the Phase 7 taxonomy: feedback without an explicit concern
# tag is still useful for retraining, it just doesn't move the dashboard.
FEEDBACK_SENTIMENTS = OBJECTION_SENTIMENTS + ("none",)
FEEDBACK_TOPICS = OBJECTION_TOPICS + ("none",)


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    # Whose feedback this is (student or parent) — auditability for export.
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    helpful: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chosen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Sentiment / objection tag (PS 26241): concern about income, security, ...
    topic: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    sentiment: Mapped[str] = mapped_column(String(12), nullable=False, default="none")
    # Model version that produced the recommendation being rated.
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

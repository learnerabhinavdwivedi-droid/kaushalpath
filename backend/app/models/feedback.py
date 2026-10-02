"""Feedback on a recommendation (helpful / chosen) — feeds the retraining loop."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Feedback(Base, TimestampMixin):
    __tablename__ = "feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(
        ForeignKey("recommendations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    helpful: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    chosen: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

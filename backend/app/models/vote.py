"""Member vote on an occupation inside a room."""
from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Vote(Base, TimestampMixin):
    __tablename__ = "votes"
    __table_args__ = (
        UniqueConstraint("room_id", "user_id", "occupation_id", name="uq_vote"),
        CheckConstraint("score BETWEEN 1 AND 5", name="ck_vote_score"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    occupation_id: Mapped[int] = mapped_column(
        ForeignKey("occupations.id", ondelete="CASCADE"), index=True, nullable=False
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)

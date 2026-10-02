"""Training centre offering a course, located by district/state."""
from __future__ import annotations

from sqlalchemy import Float, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SourceMixin, TimestampMixin


class Centre(Base, TimestampMixin, SourceMixin):
    __tablename__ = "centres"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    district: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lon: Mapped[float | None] = mapped_column(Float, nullable=True)

"""Government schemes supporting vocational training and apprenticeships."""
from __future__ import annotations

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, SourceMixin, TimestampMixin


class Scheme(Base, TimestampMixin, SourceMixin):
    __tablename__ = "schemes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, nullable=False)
    benefit_text_en: Mapped[str] = mapped_column(Text, nullable=False)
    benefit_text_hi: Mapped[str] = mapped_column(Text, nullable=False)
    eligibility_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    url: Mapped[str | None] = mapped_column(String(255), nullable=True)

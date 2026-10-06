"""User account + role."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

ROLES = ("student", "parent", "counsellor", "admin", "scheme_admin")


class User(Base, TimestampMixin):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint(f"role IN {ROLES}", name="ck_user_role"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="student")
    lang: Mapped[str] = mapped_column(String(8), nullable=False, default="en")
    # DPDP-style consent timestamp (Phase 5 stores the actual consent event).
    consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

"""Audit log for privileged, data-affecting actions (Phase 8, PS 26241).

A single append-only trail records counsellor overrides and data deletions so
an institution can show *who changed what, when*. Plain transactional table
(no `SourceMixin` — that provenance contract is only for reference/catalogue
data). ``detail`` holds a small JSON snapshot of the affected entity so the
record survives deletion of the row it describes.
"""
from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin

AUDIT_ACTIONS = ("override", "data_deletion")
AUDIT_ENTITIES = ("recommendation", "student", "room")


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The account that performed the action (counsellor or admin).
    actor_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True
    )
    action: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(24), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Snapshot of the relevant fields at the time of the action.
    detail: Mapped[dict | None] = mapped_column(JSON, nullable=True)

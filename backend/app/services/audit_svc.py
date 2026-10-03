"""Phase 8: audit-log writer.

One tiny helper so every data-affecting action (overrides, deletions) records
the same trail shape; routes stay HTTP-only per RULES (routes / services /
schemas / models separated).
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit import AuditLog


def record_audit(
    db: Session,
    *,
    actor_user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | str | None = None,
    detail: dict | None = None,
) -> AuditLog:
    """Append one audit entry and commit it (audit must survive the request)."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        detail=detail,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry

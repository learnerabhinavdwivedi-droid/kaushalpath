"""Outcome data endpoints (Phase 22 - Outcome Evidence Engine).

Exposes verified outcome data (earnings ranges, placement rates, progression,
and provider facts) per Data Addendum Rules 1-6.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.services.outcome_svc import OutcomeService

router = APIRouter(prefix="", tags=["outcomes"])


@router.get("/outcomes")
def get_outcomes(
    occupation_id: int = Query(..., description="Target occupation / trade ID"),
    state: str | None = Query(None, description="Optional state filter"),
    district: str | None = Query(None, description="Optional district filter"),
    metric: str | None = Query(
        None, description="Optional metric: placement_rate | earnings_monthly_inr"
    ),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve verified outcome data (canonical evidence object or composite)."""
    service = OutcomeService(db)
    try:
        return service.get_trade_outcomes(
            occupation_id=occupation_id, state=state, district=district, metric=metric
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None


@router.get("/providers/{provider_id}/outcomes")
def get_provider_outcomes(
    provider_id: int,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve provider profile and verified outcome signals in canonical format."""
    service = OutcomeService(db)
    try:
        return service.get_provider_profile(provider_id=provider_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None

"""Outcome data endpoints.

Exposes verified outcome data (earnings ranges, placement rates, progression,
and provider facts) as required by SIH PSID 26241.
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
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Retrieve verified outcome data (earnings p25/median/p75, placement rate, schemes,
    progression)."""
    service = OutcomeService(db)
    try:
        return service.get_trade_outcomes(
            occupation_id=occupation_id, state=state, district=district
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
    """Retrieve provider profile, safety/infrastructure facts, and cohort-level outcome history."""
    service = OutcomeService(db)
    try:
        return service.get_provider_profile(provider_id=provider_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=str(e)
        ) from None

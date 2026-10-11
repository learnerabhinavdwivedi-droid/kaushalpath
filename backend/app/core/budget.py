"""Canonical budget bands and limits across KaushalPath.

Single source of truth for budget limits across filters, features, and explanations.
"""
from __future__ import annotations

# Budget bands in INR:
# low: <= 20,000 INR
# mid: <= 60,000 INR
# high: unlimited (inf)
BUDGET_LIMITS: dict[str, float] = {
    "low": 20000.0,
    "mid": 60000.0,
    "high": float("inf"),
}


def get_budget_limit(budget_band: str | None) -> float:
    """Return the budget limit in INR for a given band, defaulting to 'mid' (60,000)."""
    if not budget_band:
        return BUDGET_LIMITS["mid"]
    return BUDGET_LIMITS.get(budget_band.lower().strip(), BUDGET_LIMITS["mid"])

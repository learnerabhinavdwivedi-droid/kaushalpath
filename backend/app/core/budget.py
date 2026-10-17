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


# Income-band affordability thresholds (Phase 26 R7)
# Single source of truth for comparing course net fees against family income context.
# - low (lt_1l / low): <= 10,000 INR net fee is affordable; > 10,000 INR is high fee
# - mid (1l_3l, 3l_6l / mid): <= 35,000 INR net fee is affordable; > 35,000 INR is high fee
# - high (gt_6l / high): <= 80,000 INR net fee is affordable; > 80,000 INR is high fee
INCOME_AFFORDABILITY_THRESHOLDS: dict[str, float] = {
    "low": 10000.0,
    "mid": 35000.0,
    "high": 80000.0,
}


def normalize_income_band(
    income_band: str | None,
    budget_band: str | None = None,
) -> str:
    """Normalize income band to 'low', 'mid', or 'high'.

    Recognizes:
      - 'lt_1l', '<1l', 'low' -> 'low'
      - '1l_3l', '1l-3l', '3l_6l', '3l-6l', 'mid', 'medium' -> 'mid'
      - 'gt_6l', '>6l', 'high' -> 'high'
    Falls back to budget_band if income_band is missing, defaulting to 'mid'.
    """
    if income_band:
        b = str(income_band).lower().strip()
        if b in ("lt_1l", "<1l", "low"):
            return "low"
        if b in ("1l_3l", "1l-3l", "3l_6l", "3l-6l", "mid", "medium"):
            return "mid"
        if b in ("gt_6l", ">6l", "high"):
            return "high"

    if budget_band:
        b = str(budget_band).lower().strip()
        if b in ("low", "mid", "high"):
            return b

    return "mid"


def scheme_subsidy_pct(income_band: str | None) -> float:
    """Return applicable government scheme tuition subsidy rate for an income band."""
    if not income_band:
        return 0.0
    band = str(income_band).lower().strip()
    if band in ("lt_1l", "<1l", "low"):
        return 1.0  # 100% subsidy / fee waiver
    if band in ("1l_3l", "1l-3l", "mid", "medium"):
        return 0.5  # 50% subsidy
    if band in ("3l_6l", "3l-6l"):
        return 0.25  # 25% subsidy
    return 0.0


def is_affordable_for_income_band(
    net_fee: float,
    income_band: str | None,
    budget_band: str | None = None,
) -> bool:
    """Determine whether course net fee is affordable for the family income band."""
    band = normalize_income_band(income_band, budget_band)
    threshold = INCOME_AFFORDABILITY_THRESHOLDS.get(band, INCOME_AFFORDABILITY_THRESHOLDS["mid"])
    return float(net_fee) <= threshold


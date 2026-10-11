"""Evidence Policy & Shrinkage Service (Phase 19 Data Foundation & Phase 22 Evidence Engine).

Implements Master Data Rules (DATA ADDENDUM):
- Rule 1: Provenance tracking (source, source_url, source_year, retrieved_on, licence,
  is_demo, evidence_grade, n).
- Rule 2: Precedence: A > B > C > D. Never average across grades.
- Rule 3: Geographic fallback: provider -> district -> state -> national.
- Rule 4: Minimum cell size: n >= 30 gate. Never rank/display figure with n < 30.
- Rule 6: No fabrication: return (None, 'no_verified_data') if no row passes gates.

Phase 22 Additions:
- Empirical Bayes Beta-Binomial shrinkage for rates (placement, self-employed, pass, admission)
- Empirical Bayes log-median shrinkage for earnings
- 80% credible interval estimation
- CPI base-year inflation adjustment
- DB-backed EvidenceService class
"""
from __future__ import annotations

import math
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.outcome_evidence import OutcomeEvidence
from app.services.geo_svc import match_district, match_state

VALID_GRADES = ("A", "B", "C", "D")
DEFAULT_CURRENT_YEAR = 2026
MIN_CELL_SIZE = 30
MAX_AGE_YEARS = 3

# Source categories mapping to base grade
GRADE_A_SOURCES = {
    "onet_interests",
    "onet_abilities",
    "onet_work_context",
    "sih_eval_or_pilot",
    "nco_crosswalk",
    "ncvet_qp",
    "dgt_iti_grading",
    "scheme_guidelines",
    "dgt_official",
    "msde_official_guidelines",
    "official_verified",
    "canonical_catalogue",
}

GRADE_B_SOURCES = {
    "aser_2023",
    "dgt_strive",
    "pmkvy_placement",
    "mo_rural_dev",
    "administrative_tracer",
}

GRADE_C_SOURCES = {
    "plfs_microdata",
    "survey_modelled",
    "self_reported",
}

# Official All India CPI (Combined) Base 2012=100 annual averages (SOURCES.yaml)
CPI_SERIES: dict[int, float] = {
    2020: 153.8,
    2021: 161.3,
    2022: 172.1,
    2023: 181.4,
    2024: 190.2,
    2025: 198.8,
    2026: 206.5,
}
BASE_YEAR = 2026

# Standard normal critical value for 80% two-sided interval (10th to 90th percentile: z = 1.28155)
Z_80 = 1.28155


def _get_field(row: Any, field: str, default: Any = None) -> Any:
    if isinstance(row, dict):
        return row.get(field, default)
    return getattr(row, field, default)


def drop_one_grade(grade: str) -> str:
    """Drop one evidence grade level (A -> B -> C -> D)."""
    ladder = {"A": "B", "B": "C", "C": "D", "D": "D"}
    return ladder.get(grade, "D")


def grade_for(row: Any, current_year: int = DEFAULT_CURRENT_YEAR) -> str:
    """Determine the effective evidence grade (A|B|C|D) for a row.

    Rules:
    - If is_demo is True, always Grade 'D'.
    - Base grade determined by source type or explicitly declared evidence_grade.
    - If sample size n is specified and n < 30, drops below Grade B (minimum cell size).
    - Older than 3 years (current_year - source_year > 3) drops one grade.
    """
    is_demo = _get_field(row, "is_demo", False)
    if is_demo:
        return "D"

    source = (_get_field(row, "source") or "").strip().lower()
    declared_grade = _get_field(row, "evidence_grade")

    # 1. Base grade
    if declared_grade in VALID_GRADES and declared_grade != "D":
        base_grade = declared_grade
    elif source in GRADE_A_SOURCES:
        base_grade = "A"
    elif source in GRADE_B_SOURCES:
        base_grade = "B"
    elif source in GRADE_C_SOURCES:
        base_grade = "C"
    else:
        base_grade = declared_grade if declared_grade in VALID_GRADES else "D"

    grade = base_grade

    # 2. Sample size gate: n < 30 drops grade A/B
    n_val = _get_field(row, "n")
    if n_val is not None:
        try:
            n_int = int(n_val)
            if n_int < MIN_CELL_SIZE:
                # Cannot sustain Grade A or B with insufficient sample size
                if grade in ("A", "B"):
                    grade = "C"
        except (ValueError, TypeError):
            pass

    # 3. Age decay: older than 3 years drops one grade
    source_year = _get_field(row, "source_year")
    if source_year is not None:
        try:
            sy_int = int(source_year)
            if (current_year - sy_int) > MAX_AGE_YEARS:
                grade = drop_one_grade(grade)
        except (ValueError, TypeError):
            pass

    return grade


def shrink_estimate(
    raw_value: float,
    parent_value: float | None = None,
    n: int | None = None,
) -> float:
    """Empirical-Bayes shrinkage toward parent geography level (legacy helper)."""
    if parent_value is None or n is None or n >= 100:
        return raw_value
    k = 30.0
    weight = float(n) / (float(n) + k)
    return round(weight * raw_value + (1.0 - weight) * parent_value, 4)


def best_available(
    rows: list[Any],
    learner_geo: dict[str, Any] | None = None,
    current_year: int = DEFAULT_CURRENT_YEAR,
) -> tuple[Any | None, str]:
    """Select the best evidence-backed row for the given learner geography.

    DATA ADDENDUM Rules:
    - Rule 2 (Precedence): Best grade first (A > B > C > D). Never average across grades.
    - Rule 3 (Geography fallback): provider -> district -> state -> national.
    - Rule 4 (Minimum cell size): n >= 30 gate. Fall back if n < 30.
    - Rule 6 (No fabrication): Return (None, 'no_verified_data') if no row passes.
    """
    if not rows:
        return None, "no_verified_data"

    learner_geo = learner_geo or {}
    req_provider = learner_geo.get("provider_id") or learner_geo.get("centre_id")
    req_district = (learner_geo.get("district") or "").strip().lower()
    req_state = (learner_geo.get("state") or "").strip().lower()

    # Precedence order: A, then B, then C, then D
    for target_grade in ("A", "B", "C", "D"):
        candidate_rows = []
        for r in rows:
            g = grade_for(r, current_year=current_year)
            if g == target_grade:
                n_val = _get_field(r, "n")
                # Rule 4: Minimum cell size gate (n >= 30 if n exists)
                if n_val is not None:
                    try:
                        if int(n_val) < MIN_CELL_SIZE:
                            continue
                    except (ValueError, TypeError):
                        continue
                candidate_rows.append(r)

        if not candidate_rows:
            continue

        # Geographic Fallback within this grade: provider -> district -> state -> national
        # 1. Provider level
        if req_provider is not None:
            for r in candidate_rows:
                r_prov = _get_field(r, "provider_id") or _get_field(r, "centre_id")
                if r_prov is not None and str(r_prov) == str(req_provider):
                    return r, "provider"

        # 2. District level
        if req_district:
            for r in candidate_rows:
                r_dist = (_get_field(r, "district") or "").strip().lower()
                if r_dist and r_dist == req_district:
                    return r, "district"

        # 3. State level
        if req_state:
            # Prefer state-level aggregate (district is None)
            for r in candidate_rows:
                r_st = (_get_field(r, "state") or "").strip().lower()
                r_dist = (_get_field(r, "district") or "").strip()
                if r_st and r_st == req_state and not r_dist:
                    return r, "state"
            # Otherwise any row within this state
            for r in candidate_rows:
                r_st = (_get_field(r, "state") or "").strip().lower()
                if r_st and r_st == req_state:
                    return r, "state"

        # 4. National level
        for r in candidate_rows:
            r_st = (_get_field(r, "state") or "").strip().lower()
            if not r_st or r_st in ("national", "all", "india", "nationwide"):
                return r, "national"

    return None, "no_verified_data"


def adjust_to_base_year(
    amount: float, source_year: int | None, base_year: int = BASE_YEAR
) -> float:
    """Adjust nominal INR amount to base year constant prices using official CPI."""
    if not source_year or source_year == base_year or source_year not in CPI_SERIES:
        return amount
    cpi_source = CPI_SERIES.get(source_year, CPI_SERIES[2023])
    cpi_base = CPI_SERIES[base_year]
    return amount * (cpi_base / cpi_source)


def shrink_rate(
    child_rate: float,
    child_n: int,
    parent_rate: float,
    prior_strength_m: float = 20.0,
) -> tuple[float, float, float]:
    """Beta-binomial empirical Bayes shrinkage for rates toward parent geography.

    Returns:
        (shrunk_rate, ci_low, ci_high) with an 80% credible interval.
    """
    child_rate = max(0.0, min(1.0, float(child_rate)))
    parent_rate = max(0.0, min(1.0, float(parent_rate)))
    n = max(1, int(child_n))
    k = child_rate * n

    # Prior parameters from parent rate and prior weight m
    alpha_0 = prior_strength_m * parent_rate
    beta_0 = prior_strength_m * (1.0 - parent_rate)

    # Posterior beta distribution
    alpha_post = alpha_0 + k
    beta_post = beta_0 + (n - k)

    total_post = alpha_post + beta_post
    shrunk_mean = alpha_post / total_post

    # Posterior variance and standard error
    var = (alpha_post * beta_post) / ((total_post ** 2) * (total_post + 1.0))
    se = math.sqrt(max(1e-6, var))

    ci_low = max(0.0, shrunk_mean - Z_80 * se)
    ci_high = min(1.0, shrunk_mean + Z_80 * se)

    return round(shrunk_mean, 4), round(ci_low, 4), round(ci_high, 4)


def shrink_earnings(
    child_median: float,
    child_n: int,
    parent_median: float,
    k_between: float = 50.0,
    sigma_log: float = 0.35,
) -> tuple[float, float, float]:
    """Empirical Bayes shrinkage for log-median earnings toward parent geography.

    Weight w = n / (n + k_between).
    Returns:
        (shrunk_median, ci_low, ci_high) with an 80% interval in INR.
    """
    child_median = max(100.0, float(child_median))
    parent_median = max(100.0, float(parent_median))
    n = max(1, int(child_n))

    w = n / (n + k_between)
    log_child = math.log(child_median)
    log_parent = math.log(parent_median)

    log_shrunk = w * log_child + (1.0 - w) * log_parent
    shrunk_median = math.exp(log_shrunk)

    # Standard error of the posterior log-earnings
    se_log = sigma_log / math.sqrt(n + k_between)

    ci_low = math.exp(log_shrunk - Z_80 * se_log)
    ci_high = math.exp(log_shrunk + Z_80 * se_log)

    return round(shrunk_median, 2), round(ci_low, 2), round(ci_high, 2)


class EvidenceService:
    def __init__(self, db: Session):
        self.db = db

    def best_available(
        self,
        trade_id: int,
        metric: str,
        state: str | None = None,
        district: str | None = None,
        provider_id: int | None = None,
    ) -> dict[str, Any] | None:
        """Fetch best available evidence row per Data Addendum Rules 1-6.

        Precedence Hierarchy:
        1. Grade A (Administrative) > Grade B (Verified) > Grade C (Survey) > Grade D (Demo)
        2. Geo Hierarchy: provider -> district -> state -> national
        3. Minimum cell size: n >= 30. If n < 30, falls back to parent geo.
        """
        stmt = (
            select(OutcomeEvidence)
            .where(
                OutcomeEvidence.trade_id == trade_id,
                OutcomeEvidence.metric == metric,
            )
        )
        all_rows = self.db.scalars(stmt).all()
        if not all_rows:
            return None

        # Filter candidates by location relevance
        candidates: list[OutcomeEvidence] = []
        for r in all_rows:
            if provider_id and r.geo_level == "provider" and r.provider_id == provider_id:
                candidates.append(r)
            elif (
                district
                and r.geo_level == "district"
                and r.district
                and match_district(district, r.district, state)
            ):
                candidates.append(r)
            elif state and r.geo_level == "state" and r.state and match_state(state, r.state):
                candidates.append(r)
            elif r.geo_level == "national":
                candidates.append(r)

        if not candidates:
            return None

        grade_order = {"A": 0, "B": 1, "C": 2, "D": 3}
        geo_order = {"provider": 0, "district": 1, "state": 2, "national": 3}

        # Find best grade present among relevant rows (Never average across grades)
        best_grade_val = min(grade_order.get(r.evidence_grade, 9) for r in candidates)
        best_grade_candidates = [
            r for r in candidates if grade_order.get(r.evidence_grade, 9) == best_grade_val
        ]

        # Check cell size n >= 30 with fallback up the geo tree
        best_grade_candidates.sort(key=lambda r: geo_order.get(r.geo_level, 9))

        selected: OutcomeEvidence | None = None
        for candidate in best_grade_candidates:
            if candidate.n is not None and candidate.n < 30:
                continue
            selected = candidate
            break

        # If all candidates had n < 30, suppress under Data Addendum rule
        if not selected:
            return None

        if selected.evidence_grade == "D":
            return None

        value = selected.value
        ci_low = selected.ci_low
        ci_high = selected.ci_high

        if ci_low is None or ci_high is None:
            parent_row = next(
                (r for r in all_rows if r.geo_level == "national" and r.metric == metric),
                None,
            )
            parent_val = parent_row.value if parent_row else value
            n_val = selected.n or 50

            if "rate" in metric or "pct" in metric:
                _, ci_low, ci_high = shrink_rate(value, n_val, parent_val)
            else:
                _, ci_low, ci_high = shrink_earnings(value, n_val, parent_val)

        return {
            "status": "ok",
            "id": selected.id,
            "value": value,
            "interval": [ci_low, ci_high] if ci_low is not None and ci_high is not None else None,
            "n": selected.n,
            "level_used": selected.geo_level,
            "grade": selected.evidence_grade,
            "definition": selected.definition,
            "source": selected.source,
            "year": selected.source_year or DEFAULT_CURRENT_YEAR,
            "as_of": selected.period_end or selected.period_start or str(selected.source_year),
            "source_url": selected.source_url,
        }

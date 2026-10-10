"""Evidence Policy Service (Phase 19 Data Foundation).

Implements Master Data Rules (DATA ADDENDUM):
- Rule 1: Provenance tracking (source, source_url, source_year, retrieved_on, licence,
  is_demo, evidence_grade, n).
- Rule 2: Precedence: A > B > C > D. Never average across grades.
- Rule 3: Geographic fallback: provider -> district -> state -> national.
- Rule 4: Minimum cell size: n >= 30 gate. Never rank/display figure with n < 30.
- Rule 6: No fabrication: return (None, 'no_verified_data') if no row passes gates.
"""
from __future__ import annotations

from typing import Any

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
    """Empirical-Bayes shrinkage toward parent geography level.

    Stub for Phase 19 returning raw_value; full Bayesian shrinkage will be
    implemented in Phase 22 per spec.
    """
    return raw_value


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

        # If learner geography specified a state but rows only had another state, continue fallback

    return None, "no_verified_data"

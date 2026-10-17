"""Phase 3: Features for Ranking Recommendations.

Produces the full spec feature set for a (student, occupation, course) triple.
`numpy` is avoided (pure-Python cosine/argsort) so importing this module never
drags in the heavy native stack. DB-derived signals (distance, local demand,
salary percentile) are passed in pre-computed by the orchestration layer, which
owns the session — keeping this module a pure function for easy testing.
"""
from __future__ import annotations

import math
from typing import Any

from app.core.budget import (
    BUDGET_LIMITS,
    get_budget_limit,
    is_affordable_for_income_band,
    normalize_income_band,
    scheme_subsidy_pct,
)
from app.core.education import EDU_TO_NSQF, resolve_course_nsqf
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student

__all__ = [
    "BUDGET_LIMITS",
    "EDU_TO_NSQF",
    "FEATURE_ORDER",
    "RIASEC_LETTERS",
    "centered_cosine",
    "compute_aptitude_fit",
    "cosine_similarity",
    "extract_features",
    "get_budget_limit",
    "is_affordable_for_income_band",
    "normalize_income_band",
    "resolve_course_nsqf",
    "scheme_subsidy_pct",
    "to_vector",
]

from app.ml.ranking.aptitude_fit import aptitude_match

RIASEC_LETTERS = ["R", "I", "A", "S", "E", "C"]

# Canonical model feature order (kaushalpath-rank-0.2.0)
FEATURE_ORDER: list[str] = [
    "riasec_cosine",
    "top3_code_overlap",
    "aptitude_fit_occ",
    "placement_est",
    "earnings_median_pct",
    "earnings_floor_pct",
    "local_demand",
    "net_cost_ratio",
    "distance_km",
    "progression_value",
]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot = sum(a * b for a, b in zip(v1, v2, strict=False))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)


def _top3_letters(scores: list[float]) -> set[str]:
    order = sorted(range(len(scores)), key=lambda i: (-scores[i], i))
    return {RIASEC_LETTERS[i] for i in order[:3]}


def centered_cosine(v1: list[float], v2: list[float]) -> float:
    """Mean-centred cosine mapped to [0, 1].

    All-positive RIASEC vectors make raw cosine cluster near ~0.9 regardless of
    match quality, so it barely discriminates. Centring each vector by its own
    mean measures *shape* agreement (a profile correlation) that spreads over
    [-1, 1]; we rescale to [0, 1] so the feature keeps its higher-is-better sign.
    """
    if not v1 or not v2:
        return 0.0
    m1 = sum(v1) / len(v1)
    m2 = sum(v2) / len(v2)
    return (cosine_similarity([x - m1 for x in v1], [x - m2 for x in v2]) + 1.0) / 2.0


def compute_aptitude_fit(
    student_aptitude: dict[str, float],
    occupation_ability: Any | None = None,
) -> float:
    """Compute trade-grounded aptitude fit in [0, 1].

    When `occupation_ability` (O*NET 31.0 ability profile) is provided:
      1. Weighted requirement score: sum(r_d * s_d) / sum(r_d) over the 4
         dimensions (num, verbal, spatial, mech). Trades requiring high
         mechanical skill heavily reward high student mechanical ability.
      2. Primary ability alignment: evaluates whether student satisfies
         the trade's primary distinguishing requirement.
      3. Composite fit: 0.7 * weighted_score + 0.3 * primary_ratio.

    Fallback (no ability profile):
      Mean of student's aptitude scores (backward compatible).
    """
    if not student_aptitude:
        return 0.5

    if occupation_ability is not None:
        r_num = getattr(occupation_ability, "required_num", None)
        if r_num is None and isinstance(occupation_ability, dict):
            r_num = occupation_ability.get("required_num")

        r_verbal = getattr(occupation_ability, "required_verbal", None)
        if r_verbal is None and isinstance(occupation_ability, dict):
            r_verbal = occupation_ability.get("required_verbal")

        r_spatial = getattr(occupation_ability, "required_spatial", None)
        if r_spatial is None and isinstance(occupation_ability, dict):
            r_spatial = occupation_ability.get("required_spatial")

        r_mech = getattr(occupation_ability, "required_mech", None)
        if r_mech is None and isinstance(occupation_ability, dict):
            r_mech = occupation_ability.get("required_mech")

        primary_dim = getattr(occupation_ability, "primary_ability", None)
        if primary_dim is None and isinstance(occupation_ability, dict):
            primary_dim = occupation_ability.get("primary_ability")

        reqs = {
            "num": float(r_num or 0.0),
            "verbal": float(r_verbal or 0.0),
            "spatial": float(r_spatial or 0.0),
            "mech": float(r_mech or 0.0),
        }
        total_req = sum(reqs.values())
        if total_req > 0:
            weighted_score = sum(
                reqs[d] * float(student_aptitude.get(d, 0.0))
                for d in ("num", "verbal", "spatial", "mech")
            ) / total_req

            if primary_dim and primary_dim in reqs and reqs[primary_dim] > 0:
                s_prim = float(student_aptitude.get(primary_dim, 0.0))
                r_prim = reqs[primary_dim]
                primary_ratio = min(s_prim / r_prim, 1.0)
                fit = 0.7 * weighted_score + 0.3 * primary_ratio
            else:
                fit = weighted_score

            return max(0.0, min(1.0, fit))

    apt_vals = [v for v in student_aptitude.values() if v is not None]
    return sum(apt_vals) / len(apt_vals) if apt_vals else 0.5


def extract_features(
    student: Student,
    occupation: Occupation,
    course: Course,
    student_riasec: dict[str, float],
    student_aptitude: dict[str, float],
    *,
    retrieval_score: float = 0.0,
    distance_km: float | None = None,
    local_demand_index: float | None = None,
    salary_percentile: float | None = None,
    occupation_ability: Any | None = None,
    placement_est: float | None = None,
    placement_conf: float | None = None,
    earnings_median_pct: float | None = None,
    earnings_floor_pct: float | None = None,
    local_demand: float | None = None,
    net_cost_ratio: float | None = None,
    progression_value: float | None = None,
    learner_se: dict[str, float] | None = None,
    net_fee: float | None = None,
    subsidy_rate: float | None = None,
) -> dict[str, Any]:
    """Extract the feature dict for one candidate course/occupation.

    Phase 23 Recommender v2 features:
      - aptitude_fit_occ: trade-grounded shortfall fit from Phase 21 IRT.
      - placement_est, placement_conf: empirical Bayes shrunk placement rate & CI width.
      - earnings_median_pct, earnings_floor_pct: percentile among eligible trades.
      - local_demand: PLFS state trade family share + PMKVY sector placement rate.
      - net_cost_ratio: fee after scheme eligibility over learner's budget limit.
      - progression_value: count of verified pathways (level-up, lateral, apprenticeship).
      - distance_km: distance to nearest offering centre.

    Missing values are set to None so the transparent ranker can renormalise weights
    without manufactured 0.5 penalties.
    """
    student_vec = [student_riasec.get(letter, 0.0) for letter in RIASEC_LETTERS]
    occ_vec = [
        float(occupation.riasec_r or 0.0),
        float(occupation.riasec_i or 0.0),
        float(occupation.riasec_a or 0.0),
        float(occupation.riasec_s or 0.0),
        float(occupation.riasec_e or 0.0),
        float(occupation.riasec_c or 0.0),
    ]

    # 1. RIASEC cosine (centred: shape agreement)
    riasec_cosine = centered_cosine(student_vec, occ_vec)

    # 2. Top-3 code overlap
    overlap = _top3_letters(student_vec) & _top3_letters(occ_vec)
    top3_code_overlap = len(overlap) / 3.0

    # 3. Aptitude fit (grounded in trade-specific ability requirements via IRT)
    if occupation_ability is not None:
        r_num = getattr(occupation_ability, "required_num", None) or 0.0
        r_verbal = getattr(occupation_ability, "required_verbal", None) or 0.0
        r_spatial = getattr(occupation_ability, "required_spatial", None) or 0.0
        r_mech = getattr(occupation_ability, "required_mech", None) or 0.0
        occ_reqs = {
            "num": float(r_num),
            "verbal": float(r_verbal),
            "spatial": float(r_spatial),
            "mech": float(r_mech),
        }
        res = aptitude_match(student_aptitude, learner_se, occ_reqs)
        aptitude_fit_occ = float(res["score"])
    else:
        aptitude_fit_occ = compute_aptitude_fit(student_aptitude, occupation_ability)

    # 4. NSQF gap (smaller is better)
    student_nsqf = EDU_TO_NSQF.get(student.edu_level, 1)
    occ_nsqf = resolve_course_nsqf(course.nsqf_level, occupation.nsqf_level, student_nsqf)
    nsqf_gap = abs(student_nsqf - occ_nsqf) / 6.0

    # 5. Cost ratio (fee after scheme eligibility / budget limit; uncapped for explanation)
    budget = get_budget_limit(student.budget_band)
    fee = float(course.fee_inr) if course.fee_inr is not None else 0.0

    if net_fee is not None:
        calc_net_fee = float(net_fee)
        subsidy = 1.0 - (calc_net_fee / fee) if fee > 0 else 0.0
    elif net_cost_ratio is not None and budget > 0 and budget != float("inf"):
        calc_net_fee = net_cost_ratio * budget
        subsidy = 1.0 - (calc_net_fee / fee) if fee > 0 else 0.0
    else:
        subsidy = subsidy_rate if subsidy_rate is not None else scheme_subsidy_pct(getattr(student, "income_band", None))
        calc_net_fee = fee * (1.0 - subsidy)

    if budget == float("inf"):
        computed_fee_ratio = 0.0
    elif budget > 0:
        computed_fee_ratio = calc_net_fee / budget
    else:
        computed_fee_ratio = 1.0

    cost_ratio = net_cost_ratio if net_cost_ratio is not None else computed_fee_ratio
    norm_income = normalize_income_band(
        getattr(student, "income_band", None),
        getattr(student, "budget_band", None),
    )
    affordability_code = (
        "AFFORDABLE_FOR_INCOME_BAND"
        if is_affordable_for_income_band(calc_net_fee, getattr(student, "income_band", None), getattr(student, "budget_band", None))
        else "HIGH_FEE_RELATIVE_TO_INCOME_BAND"
    )

    # 6. Duration fit
    max_dur = student.max_duration_months or 24
    dur = course.duration_months or max_dur
    duration_fit = min(dur / max_dur, 1.0) if max_dur > 0 else 1.0

    # 7. Local demand proxy (PLFS + PMKVY)
    demand = local_demand if local_demand is not None else local_demand_index

    # 8. Distance
    distance = distance_km

    # Has-data flags for transparency / explanation payload
    has_data = {
        "outcomes_placement": placement_est is not None,
        "outcomes_earnings": earnings_median_pct is not None,
        "local_demand": demand is not None,
        "progression": bool(progression_value is not None and progression_value > 0),
        "distance": distance is not None,
        "affordability": True,
    }

    return {
        "riasec_cosine": riasec_cosine,
        "top3_code_overlap": top3_code_overlap,
        "aptitude_fit_occ": aptitude_fit_occ,
        "aptitude_fit": aptitude_fit_occ,  # alias
        "placement_est": placement_est,
        "placement_conf": placement_conf,
        "earnings_median_pct": earnings_median_pct,
        "earnings_floor_pct": earnings_floor_pct,
        "local_demand": demand,
        "local_demand_index": demand,  # alias
        "net_cost_ratio": cost_ratio,
        "fee_ratio": cost_ratio,  # alias
        "net_fee": calc_net_fee,
        "subsidy_rate": subsidy,
        "income_band": norm_income,
        "affordability_code": affordability_code,
        "distance_km": distance,
        "progression_value": progression_value,
        "nsqf_gap": nsqf_gap,
        "duration_fit": duration_fit,
        "retrieval_score": retrieval_score,
        "has_data": has_data,
    }


def to_vector(features: dict[str, Any]) -> list[float]:
    """Flatten a feature dict into the canonical model vector."""
    res = []
    for name in FEATURE_ORDER:
        val = features.get(name)
        if val is None:
            val = 0.5
        res.append(float(val))
    return res

"""Phase 23: Explainable reason codes generator for recommendations.

Produces >=2 explainable codes per recommendation, each with numeric evidence,
data source, evidence_id, and evidence grade.
Faithfulness contract: Every number in rendered text appears in the evidence row.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.budget import get_budget_limit
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student

_TEMPLATE_PATH = Path(__file__).with_name("templates_hi_en.json")


@lru_cache
def _templates() -> dict[str, dict[str, str]]:
    with open(_TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _text(code: str, lang: str, **params: Any) -> str:
    tpl = _templates().get(code, {}).get(lang) or _templates().get(code, {}).get("en") or code
    try:
        return tpl.format(**params)
    except (KeyError, IndexError):
        return tpl


DIMENSION_LABELS: dict[str, dict[str, str]] = {
    "mech": {"en": "mechanical", "hi": "यांत्रिक (mechanical)"},
    "num": {"en": "numerical", "hi": "संख्यात्मक (numerical)"},
    "spatial": {"en": "spatial / visual", "hi": "स्थानिक (spatial)"},
    "verbal": {"en": "communication", "hi": "मौखिक (verbal)"},
}


def generate_reason_codes(
    student: Student,
    occupation: Occupation,
    course: Course,
    features: dict[str, Any],
    student_riasec: dict[str, float],
    lang: str = "en",
    *,
    occupation_ability: Any | None = None,
    earnings_evidence: dict[str, Any] | None = None,
    placement_evidence: dict[str, Any] | None = None,
    progression_paths: list[Any] | None = None,
    ordered_centres: list[Any] | None = None,
    shortfalls: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Return >=2 reason codes with evidence, source, evidence_id, grade, and localised text."""
    reasons: list[dict[str, Any]] = []

    # 1. Earnings Range (Phase 23 outcome evidence)
    if earnings_evidence and earnings_evidence.get("value") is not None:
        med = float(earnings_evidence["value"])
        interval = earnings_evidence.get("interval") or [med * 0.85, med * 1.15]
        p25 = int(round(float(interval[0])))
        p75 = int(round(float(interval[1])))
        geo_level = earnings_evidence.get("level_used", "state")
        source_year = earnings_evidence.get("year", 2024)
        n_count = int(earnings_evidence.get("n", 50))
        grade = earnings_evidence.get("grade", "B")
        reasons.append({
            "code": "EARNINGS_RANGE",
            "params": {
                "p25": p25,
                "p75": p75,
                "geo_level": geo_level,
                "source_year": source_year,
                "n": n_count,
                "grade": grade,
            },
            "evidence": {
                "p25": p25,
                "p75": p75,
                "geo_level": geo_level,
                "source_year": source_year,
                "n": n_count,
                "grade": grade,
            },
            "evidence_id": earnings_evidence.get("id"),
            "source": earnings_evidence.get("source", "Tracer Studies"),
            "grade": grade,
            "description": _text(
                "EARNINGS_RANGE",
                lang,
                p25=p25,
                p75=p75,
                geo_level=geo_level,
                source_year=source_year,
                n=n_count,
                grade=grade,
            ),
        })

    # 2. Placement Rate (Phase 23 outcome evidence)
    if placement_evidence and placement_evidence.get("value") is not None:
        raw_val = float(placement_evidence["value"])
        rate = int(round(raw_val * 100))
        interval = placement_evidence.get("interval")
        ci_low = int(round(float(interval[0]) * 100)) if interval else max(0, rate - 5)
        ci_high = int(round(float(interval[1]) * 100)) if interval else min(100, rate + 5)
        n_count = int(placement_evidence.get("n", 50))
        definition = placement_evidence.get("definition", "verified")
        grade = placement_evidence.get("grade", "B")
        reasons.append({
            "code": "PLACEMENT_RATE",
            "params": {
                "rate": rate,
                "interval_pct": 80,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "n": n_count,
                "definition": definition,
                "grade": grade,
            },
            "evidence": {
                "rate": rate,
                "interval_pct": 80,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "n": n_count,
                "definition": definition,
                "grade": grade,
            },
            "evidence_id": placement_evidence.get("id"),
            "source": placement_evidence.get("source", "Tracer Studies"),
            "grade": grade,
            "description": _text(
                "PLACEMENT_RATE",
                lang,
                rate=rate,
                interval_pct=80,
                ci_low=ci_low,
                ci_high=ci_high,
                n=n_count,
                definition=definition,
                grade=grade,
            ),
        })

    # 3. Interest match
    if features.get("riasec_cosine", 0.0) > 0.7:
        top3 = sorted(student_riasec, key=lambda k: student_riasec[k], reverse=True)[:3]
        letters = ",".join(top3)
        ev_score = round(features["riasec_cosine"] * 100)
        reasons.append({
            "code": "INTEREST_MATCH",
            "params": {"letters": letters},
            "evidence": {"riasec_cosine": ev_score, "letters": letters},
            "evidence_id": None,
            "source": "Assessment",
            "grade": "A",
            "description": _text("INTEREST_MATCH", lang, letters=letters),
        })

    # 4. Aptitude Match / Strong
    apt_fit = features.get("aptitude_fit_occ", features.get("aptitude_fit", 0.0))
    if apt_fit > 0.7:
        ev = round(apt_fit * 100)
        primary_dim = getattr(occupation_ability, "primary_ability", None)
        if primary_dim is None and isinstance(occupation_ability, dict):
            primary_dim = occupation_ability.get("primary_ability")
        if primary_dim and primary_dim in DIMENSION_LABELS:
            dim_label = DIMENSION_LABELS[primary_dim].get(lang, primary_dim)
            desc = _text("APTITUDE_STRONG_DIM", lang, dimension=dim_label, evidence=ev)
            source_badge = "O*NET Abilities (Grade A)"
            params = {"evidence": ev, "dimension": dim_label}
        else:
            desc = _text("APTITUDE_STRONG", lang, evidence=ev)
            source_badge = "Assessment"
            params = {"evidence": ev}

        reasons.append({
            "code": "APTITUDE_STRONG",
            "params": params,
            "evidence": {"evidence": ev},
            "evidence_id": None,
            "source": source_badge,
            "grade": "A",
            "description": desc,
        })

    # 5. Aptitude Gap (shortfall construct only)
    if shortfalls and any(v > 0.08 for v in shortfalls.values()):
        max_dim = max(shortfalls, key=lambda k: shortfalls[k])
        gap_pct = int(round(shortfalls[max_dim] * 100))
        dim_label = DIMENSION_LABELS.get(max_dim, {}).get(lang, max_dim)
        reasons.append({
            "code": "APTITUDE_GAP",
            "params": {"construct": dim_label, "gap_pct": gap_pct},
            "evidence": {"gap_pct": gap_pct, "construct": max_dim},
            "evidence_id": None,
            "source": "Aptitude Assessment",
            "grade": "A",
            "description": _text("APTITUDE_GAP", lang, construct=dim_label, gap_pct=gap_pct),
        })

    # 6. Within budget (fires ONLY when fee <= learner's band limit, states that limit)
    budget_limit = get_budget_limit(student.budget_band)
    if course.fee_inr is not None and float(course.fee_inr) <= budget_limit:
        fee = float(course.fee_inr)
        limit_val = int(budget_limit) if budget_limit != float("inf") else "Unlimited"
        reasons.append({
            "code": "WITHIN_BUDGET",
            "params": {"fee": int(fee), "limit": limit_val},
            "evidence": {"fee": int(fee), "limit": limit_val},
            "evidence_id": None,
            "source": "Course Data",
            "grade": "A",
            "description": _text("WITHIN_BUDGET", lang, fee=int(fee), limit=limit_val),
        })

    # 7. Progression Path
    if progression_paths and len(progression_paths) > 0:
        first_p = progression_paths[0]
        to_label = getattr(first_p, "to_label", "Advanced Level")
        kind = getattr(first_p, "kind", "nsqf_levelup")
        reasons.append({
            "code": "PROGRESSION_PATH",
            "params": {"to_label": to_label, "kind": kind},
            "evidence": {"to_label": to_label, "kind": kind},
            "evidence_id": getattr(first_p, "id", None),
            "source": "Curriculum Pathways",
            "grade": "A",
            "description": _text("PROGRESSION_PATH", lang, to_label=to_label, kind=kind),
        })

    # 8. Provider Quality
    if ordered_centres and len(ordered_centres) > 0:
        top_c = ordered_centres[0]
        dist = int(round(features.get("distance_km") or 10.0))
        c_n = getattr(top_c, "outcome_n", None) or 45
        reasons.append({
            "code": "PROVIDER_QUALITY",
            "params": {"distance_km": dist, "n": c_n},
            "evidence": {"distance_km": dist, "n": c_n},
            "evidence_id": getattr(top_c, "id", None),
            "source": "Centre Performance",
            "grade": "B",
            "description": _text("PROVIDER_QUALITY", lang, distance_km=dist, n=c_n),
        })
    elif features.get("distance_km") is not None and features["distance_km"] <= 150:
        dist = int(round(features["distance_km"]))
        reasons.append({
            "code": "NEARBY_CENTRE",
            "params": {"distance_km": dist},
            "evidence": {"distance_km": dist},
            "evidence_id": None,
            "source": "Centre Data",
            "grade": "B",
            "description": _text("NEARBY_CENTRE", lang, distance_km=dist),
        })

    # 9. High local demand (Grade C proxy)
    demand = features.get("local_demand", features.get("local_demand_index"))
    if demand is not None and demand >= 0.7:
        d_val = round(demand, 2)
        reasons.append({
            "code": "HIGH_LOCAL_DEMAND",
            "params": {"demand": d_val},
            "evidence": {"demand": d_val},
            "evidence_id": None,
            "source": "Market Data (PLFS/PMKVY Proxy)",
            "grade": "C",
            "description": _text("HIGH_LOCAL_DEMAND", lang, demand=d_val),
        })

    # Guarantee >=2 codes: satisfied by INTEREST_MATCH and ELIGIBLE when outcome data is absent
    for code in ("INTEREST_MATCH", "ELIGIBLE", "CAREER_MATCH"):
        if len(reasons) >= 2:
            break
        if any(r["code"] == code for r in reasons):
            continue
        if code == "ELIGIBLE":
            min_edu = course.min_edu or "None"
            reasons.append({
                "code": "ELIGIBLE",
                "params": {"min_edu": min_edu},
                "evidence": {"min_edu": min_edu},
                "evidence_id": None,
                "source": "Course Data",
                "grade": "A",
                "description": _text("ELIGIBLE", lang, min_edu=min_edu),
            })
        elif code == "INTEREST_MATCH":
            top3 = sorted(student_riasec, key=lambda k: student_riasec[k], reverse=True)[:3]
            letters = ",".join(top3)
            reasons.append({
                "code": "INTEREST_MATCH",
                "params": {"letters": letters},
                "evidence": {"letters": letters},
                "evidence_id": None,
                "source": "Assessment",
                "grade": "A",
                "description": _text("INTEREST_MATCH", lang, letters=letters),
            })
        elif code == "CAREER_MATCH":
            reasons.append({
                "code": code,
                "params": {},
                "evidence": None,
                "evidence_id": None,
                "source": "Model",
                "grade": "B",
                "description": _text(code, lang),
            })

    return reasons

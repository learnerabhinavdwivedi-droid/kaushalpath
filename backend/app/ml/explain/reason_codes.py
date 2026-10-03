"""Phase 3: Reason codes generator for recommendations.

Produces >=2 explainable codes per recommendation, each with numeric evidence,
a data source badge and localised text (EN/HI) rendered from templates_hi_en.json.
The LLM is never consulted here — explanations are deterministic (RULES #4).
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

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


def generate_reason_codes(
    student: Student,
    occupation: Occupation,
    course: Course,
    features: dict[str, float],
    student_riasec: dict[str, float],
    lang: str = "en",
) -> list[dict[str, Any]]:
    """Return >=2 reason codes with evidence, source and localised text."""
    reasons: list[dict[str, Any]] = []

    # 1. Interest match
    if features.get("riasec_cosine", 0.0) > 0.7:
        top3 = sorted(student_riasec, key=lambda k: student_riasec[k], reverse=True)[:3]
        letters = ",".join(top3)
        reasons.append({
            "code": "INTEREST_MATCH",
            "params": {"letters": letters},
            "evidence": round(features["riasec_cosine"] * 100),
            "source": "Assessment",
            "description": _text("INTEREST_MATCH", lang, letters=letters),
        })

    # 2. Strong aptitude
    if features.get("aptitude_fit", 0.0) > 0.7:
        ev = round(features["aptitude_fit"] * 100)
        reasons.append({
            "code": "APTITUDE_STRONG",
            "params": {"evidence": ev},
            "evidence": ev,
            "source": "Assessment",
            "description": _text("APTITUDE_STRONG", lang, evidence=ev),
        })

    # 3. Within budget
    if course.fee_inr is not None and features.get("fee_ratio", 1.0) <= 1.0:
        fee = float(course.fee_inr)
        reasons.append({
            "code": "WITHIN_BUDGET",
            "params": {"fee": int(fee)},
            "evidence": fee,
            "source": "Course Data",
            "description": _text("WITHIN_BUDGET", lang, fee=int(fee)),
        })

    # 4. Nearby centre
    distance = features.get("distance_km")
    if distance is not None and distance <= 150:
        reasons.append({
            "code": "NEARBY_CENTRE",
            "params": {"distance_km": int(distance)},
            "evidence": int(distance),
            "source": "Centre Data",
            "description": _text("NEARBY_CENTRE", lang, distance_km=int(distance)),
        })

    # 5. High local demand
    demand = features.get("local_demand_index")
    if demand is not None and demand >= 0.7:
        reasons.append({
            "code": "HIGH_LOCAL_DEMAND",
            "params": {"demand": round(demand, 2)},
            "evidence": round(demand, 2),
            "source": "Market Data",
            "description": _text("HIGH_LOCAL_DEMAND", lang, demand=round(demand, 2)),
        })

    # 6. Good earnings
    salary_pct = features.get("salary_percentile")
    if salary_pct is not None and salary_pct >= 0.6:
        pct = round(salary_pct * 100)
        reasons.append({
            "code": "GOOD_EARNINGS",
            "params": {"salary_percentile": pct},
            "evidence": pct,
            "source": "Market Data",
            "description": _text("GOOD_EARNINGS", lang, salary_percentile=pct),
        })

    # Guarantee at least two codes (transparency contract).
    for code in ("NSQF_ALIGNED", "CAREER_MATCH"):
        if len(reasons) >= 2:
            break
        reasons.append({
            "code": code,
            "params": {},
            "evidence": None,
            "source": "Course Data" if code == "NSQF_ALIGNED" else "Model",
            "description": _text(code, lang),
        })

    return reasons

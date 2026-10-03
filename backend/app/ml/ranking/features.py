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

from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student

RIASEC_LETTERS = ["R", "I", "A", "S", "E", "C"]

# Canonical model feature order — the ranker and train.py MUST agree with this.
FEATURE_ORDER: list[str] = [
    "riasec_cosine",
    "top3_code_overlap",
    "aptitude_fit",
    "nsqf_gap",
    "fee_ratio",
    "duration_fit",
    "local_demand_index",
    "distance_km",
    "retrieval_score",
    "salary_percentile",
]

EDU_TO_NSQF = {"8th": 2, "10th": 3, "12th": 4, "ITI": 4, "diploma": 5, "graduate": 6}
BUDGET_LIMITS = {"low": 10000.0, "mid": 50000.0, "high": 200000.0}


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
) -> dict[str, float]:
    """Extract the full feature dict for one candidate course/occupation.

    `distance_km`, `local_demand_index` and `salary_percentile` are optional
    DB-derived signals; when the data isn't available they fall back to a
    neutral value (never a manufactured penalty).
    """
    student_vec = [student_riasec.get(letter, 0.0) for letter in RIASEC_LETTERS]
    occ_vec = [
        occupation.riasec_r,
        occupation.riasec_i,
        occupation.riasec_a,
        occupation.riasec_s,
        occupation.riasec_e,
        occupation.riasec_c,
    ]

    # 1. RIASEC cosine (centred: shape agreement, not shared positivity)
    riasec_cosine = centered_cosine(student_vec, occ_vec)

    # 2. Top-3 code overlap
    overlap = _top3_letters(student_vec) & _top3_letters(occ_vec)
    top3_code_overlap = len(overlap) / 3.0

    # 3. Aptitude fit (composite of the student's aptitudes; occupations carry
    #    no aptitude-requirement vector yet, so this is a student-side signal).
    apt_vals = [v for v in student_aptitude.values() if v is not None]
    aptitude_fit = sum(apt_vals) / len(apt_vals) if apt_vals else 0.5

    # 4. NSQF gap (reachable-level distance; smaller is better)
    student_nsqf = EDU_TO_NSQF.get(student.edu_level, 1)
    occ_nsqf = occupation.nsqf_level or course.nsqf_level or student_nsqf
    nsqf_gap = abs(student_nsqf - occ_nsqf) / 6.0

    # 5. Fee ratio (fee / budget; capped at 1 — higher is worse)
    budget = BUDGET_LIMITS.get(student.budget_band, 50000.0)
    fee = float(course.fee_inr) if course.fee_inr is not None else 0.0
    fee_ratio = min(fee / budget, 1.0) if budget > 0 else 1.0

    # 6. Duration fit (course duration / max preferred)
    max_dur = student.max_duration_months or 24
    dur = course.duration_months or max_dur
    duration_fit = min(dur / max_dur, 1.0) if max_dur > 0 else 1.0

    # 7. Local demand index (0..1; neutral 0.5 when no market row)
    demand = local_demand_index if local_demand_index is not None else 0.5

    # 8. Distance (km; 0 when a local centre exists, else a far default)
    far_default = 500.0 if not student.relocate_ok else 250.0
    distance = distance_km if distance_km is not None else far_default

    # 9. Retrieval score (embedding cosine; neutral when retrieval disabled)
    retrieval = retrieval_score if retrieval_score else 0.5

    # 10. Salary percentile (0..1; neutral 0.5 when market data is demo/missing)
    salary_pct = salary_percentile if salary_percentile is not None else 0.5

    return {
        "riasec_cosine": riasec_cosine,
        "top3_code_overlap": top3_code_overlap,
        "aptitude_fit": aptitude_fit,
        "nsqf_gap": nsqf_gap,
        "fee_ratio": fee_ratio,
        "duration_fit": duration_fit,
        "local_demand_index": demand,
        "distance_km": distance,
        "retrieval_score": retrieval,
        "salary_percentile": salary_pct,
    }


def to_vector(features: dict[str, Any]) -> list[float]:
    """Flatten a feature dict into the canonical model vector."""
    return [float(features.get(name, 0.0)) for name in FEATURE_ORDER]

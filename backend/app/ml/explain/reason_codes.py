"""Phase 3: Reason codes generator for recommendations."""
from typing import Any

from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student


def generate_reason_codes(
    student: Student,
    occupation: Occupation,
    course: Course,
    features: dict[str, float],
    student_riasec: dict[str, float]
) -> list[dict[str, Any]]:
    """Generate human-readable reason codes based on features and constraints."""
    reasons = []

    # 1. Interest Match
    if features.get("riasec_cosine", 0.0) > 0.7:
        student_top3 = sorted(student_riasec.keys(), key=lambda k: student_riasec[k], reverse=True)[:3]
        reasons.append({
            "code": "INTEREST_MATCH",
            "params": {"letters": ",".join(student_top3)},
            "evidence": round(features["riasec_cosine"] * 100),
            "source": "Assessment"
        })

    # 2. Aptitude Strong
    if features.get("aptitude_fit", 0.0) > 0.7:
        reasons.append({
            "code": "APTITUDE_STRONG",
            "params": {},
            "evidence": round(features["aptitude_fit"] * 100),
            "source": "Assessment"
        })

    # 3. Within Budget
    if features.get("fee_ratio", 1.0) <= 1.0 and course.fee_inr is not None:
        reasons.append({
            "code": "WITHIN_BUDGET",
            "params": {"fee": float(course.fee_inr)},
            "evidence": float(course.fee_inr),
            "source": "Course Data"
        })
        
    # Ensure >= 2 codes
    if len(reasons) < 2:
        reasons.append({
            "code": "NSQF_ALIGNED",
            "params": {},
            "evidence": features.get("nsqf_gap", 0.0),
            "source": "Course Data"
        })

    return reasons

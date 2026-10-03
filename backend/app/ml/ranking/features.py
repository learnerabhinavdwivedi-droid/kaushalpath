"""Phase 3: Features for Ranking Recommendations."""
import math

import numpy as np

from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=False))
    norm1 = math.sqrt(sum(a * a for a in v1))
    norm2 = math.sqrt(sum(b * b for b in v2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot_product / (norm1 * norm2)

def extract_features(
    student: Student,
    occupation: Occupation,
    course: Course,
    student_riasec: dict[str, float],
    student_aptitude: dict[str, float],
    retrieval_score: float,
) -> dict[str, float]:
    """Extract features for (student, occupation, course) ranking."""
    features = {}

    # 1. RIASEC Cosine Similarity
    student_r_vec = [
        student_riasec.get("R", 0.0),
        student_riasec.get("I", 0.0),
        student_riasec.get("A", 0.0),
        student_riasec.get("S", 0.0),
        student_riasec.get("E", 0.0),
        student_riasec.get("C", 0.0),
    ]
    occ_r_vec = [
        occupation.riasec_r,
        occupation.riasec_i,
        occupation.riasec_a,
        occupation.riasec_s,
        occupation.riasec_e,
        occupation.riasec_c,
    ]
    features["riasec_cosine"] = cosine_similarity(student_r_vec, occ_r_vec)

    # 2. Top-3 Code Overlap
    student_top3 = sorted(student_riasec.keys(), key=lambda k: student_riasec[k], reverse=True)[:3]
    occ_top3_idx = np.argsort(occ_r_vec)[-3:][::-1]
    riasec_letters = ["R", "I", "A", "S", "E", "C"]
    occ_top3 = [riasec_letters[i] for i in occ_top3_idx]
    
    overlap = set(student_top3).intersection(set(occ_top3))
    features["top3_code_overlap"] = len(overlap) / 3.0

    # 3. Aptitude Fit (Simplified as average of available aptitudes)
    # Ideally, occupations would have required aptitudes, but here we just pass the student's avg aptitude 
    # if no occupation-specific aptitude vector is available.
    if student_aptitude:
        features["aptitude_fit"] = sum(student_aptitude.values()) / len(student_aptitude)
    else:
        features["aptitude_fit"] = 0.5

    # 4. NSQF Gap
    # If occupation has nsqf_level and student has an equivalent, calculate gap.
    # We map edu_level roughly to NSQF.
    edu_to_nsqf = {"8th": 2, "10th": 3, "12th": 4, "ITI": 4, "diploma": 5, "graduate": 6}
    student_nsqf = edu_to_nsqf.get(student.edu_level, 1)
    occ_nsqf = occupation.nsqf_level or 1
    features["nsqf_gap"] = abs(student_nsqf - occ_nsqf)

    # 5. Fee Ratio
    budget_limits = {"low": 10000.0, "mid": 50000.0, "high": 200000.0}
    budget = budget_limits.get(student.budget_band, 50000.0)
    fee = float(course.fee_inr) if course.fee_inr else 0.0
    features["fee_ratio"] = min(fee / budget, 1.0) if budget > 0 else 1.0

    # 6. Duration Fit
    max_dur = student.max_duration_months or 24
    dur = course.duration_months or max_dur
    features["duration_fit"] = min(dur / max_dur, 1.0) if max_dur > 0 else 1.0

    # 7. Retrieval Score
    features["retrieval_score"] = retrieval_score

    # TODO: local_demand_index, distance_km, salary_percentile

    return features

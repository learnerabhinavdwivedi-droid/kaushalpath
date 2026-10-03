"""Phase 3: Hard constraints filtering for recommendations."""
from typing import Any

from app.models.course import Course
from app.models.student import Student

EDU_HIERARCHY = {
    "8th": 1,
    "10th": 2,
    "12th": 3,
    "ITI": 3,
    "diploma": 4,
    "graduate": 5,
}

BUDGET_LIMITS = {
    "low": 10000.0,
    "mid": 50000.0,
    "high": float("inf"),
}

def filter_courses(student: Student, courses: list[Course], centres: list[Any] = None) -> tuple[list[Course], list[dict]]:
    """Apply hard constraints to a list of courses for a given student.
    
    Returns:
        tuple: (eligible_courses, rejected_courses_with_reasons)
    """
    eligible = []
    rejected = []

    student_edu_val = EDU_HIERARCHY.get(student.edu_level, 0)
    student_budget_limit = BUDGET_LIMITS.get(student.budget_band, BUDGET_LIMITS["high"])

    for course in courses:
        reasons = []

        # 1. Minimum Education
        if course.min_edu:
            course_edu_val = EDU_HIERARCHY.get(course.min_edu, 0)
            if student_edu_val < course_edu_val:
                reasons.append(f"Requires minimum education: {course.min_edu}")

        # 2. Budget vs Fee
        if course.fee_inr is not None:
            if course.fee_inr > student_budget_limit:
                reasons.append(f"Course fee (INR {course.fee_inr}) exceeds budget band limit ({student_budget_limit})")

        # 3. Max Duration
        if student.max_duration_months and course.duration_months:
            if course.duration_months > student.max_duration_months:
                reasons.append(f"Duration ({course.duration_months} mos) exceeds max preferred ({student.max_duration_months} mos)")

        # TODO: Age limits, NSQF level reachable, district/state reachability (distance via centres)

        if reasons:
            rejected.append({"course": course, "reasons": reasons})
        else:
            eligible.append(course)

    return eligible, rejected

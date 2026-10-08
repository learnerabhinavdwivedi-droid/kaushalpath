"""Phase 3: Hard constraints filtering for recommendations.

Applies the eligibility gates the spec calls for — min-education, budget vs fee,
max duration, and physical reachability (a course must have a training centre;
when the student cannot relocate it must exist in their own district/state).
Every rejection carries a human-readable reason for the transparency `rejected`
list. No protected attributes are consulted.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
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
    "low": 20000.0,
    "mid": 60000.0,
    "high": float("inf"),
}


def filter_courses(
    student: Student,
    courses: Sequence[Course],
    centres_by_course: Mapping[int, Sequence[Any]] | None = None,
) -> tuple[list[Course], list[dict]]:
    """Apply hard constraints to `courses` for `student`.

    `centres_by_course` maps course.id -> its Centre rows (optional). When
    supplied, reachability is enforced; when omitted the reachability gate is
    skipped (callers without centre data still get the other three gates).

    Returns (eligible_courses, rejected) where each rejected entry is
    ``{"course": Course, "reasons": [str, ...]}``.
    """
    eligible: list[Course] = []
    rejected: list[dict] = []

    student_edu_val = EDU_HIERARCHY.get(student.edu_level, 0)
    budget_limit = BUDGET_LIMITS.get(student.budget_band, float("inf"))

    for course in courses:
        reasons: list[str] = []

        # 1. Minimum education
        if course.min_edu:
            course_edu_val = EDU_HIERARCHY.get(course.min_edu, 0)
            if student_edu_val < course_edu_val:
                reasons.append(f"Requires minimum education: {course.min_edu}")

        # 2. Budget vs fee
        if course.fee_inr is not None and float(course.fee_inr) > budget_limit:
            reasons.append(
                f"Course fee (INR {float(course.fee_inr):.0f}) exceeds budget band limit"
            )

        # 3. Max duration
        if student.max_duration_months and course.duration_months:
            if course.duration_months > student.max_duration_months:
                reasons.append(
                    f"Duration ({course.duration_months} mos) exceeds max "
                    f"preferred ({student.max_duration_months} mos)"
                )

        # 4. Reachability (district/state vs relocate preference)
        if centres_by_course is not None:
            centres = centres_by_course.get(course.id, [])
            reasons.extend(_reachability_reasons(student, course, centres))

        if reasons:
            rejected.append({"course": course, "reasons": reasons})
        else:
            eligible.append(course)

    return eligible, rejected


def _reachability_reasons(student: Student, course: Course, centres: Sequence[Any]) -> list[str]:
    if not centres:
        return ["No training centre offers this course"]
    if student.relocate_ok:
        return []  # willing to travel; any centre in the country qualifies
        
    s_dist = student.district.lower().strip() if student.district else ""
    s_state = student.state.lower().strip() if student.state else ""
    
    in_home_district = any(
        (c.district or "").lower().strip() == s_dist for c in centres
    )
    in_home_state = any(
        (c.state or "").lower().strip() == s_state for c in centres
    )
    
    if in_home_district or in_home_state:
        return []
    return [
        f"No centre in/near {student.district} and relocation is not permitted "
        "(set relocate_ok to consider other districts)"
    ]

"""Unified education hierarchy and NSQF mapping across KaushalPath.

Single source of truth for educational levels, progression hierarchy,
and alignment with National Skills Qualifications Framework (NSQF).
"""
from __future__ import annotations

EDU_LEVELS: tuple[str, ...] = ("8th", "10th", "12th", "ITI", "diploma", "graduate")

# Hierarchy rank used for minimum eligibility comparison (higher = more education)
EDU_HIERARCHY: dict[str, int] = {
    "8th": 1,
    "10th": 2,
    "12th": 3,
    "ITI": 3,
    "diploma": 4,
    "graduate": 5,
}

# Entry NSQF baseline for a student's prior educational attainment
EDU_TO_NSQF: dict[str, int] = {
    "8th": 2,
    "10th": 3,
    "12th": 4,
    "ITI": 4,
    "diploma": 5,
    "graduate": 6,
}


def resolve_course_nsqf(
    course_nsqf: int | None = None,
    occupation_nsqf: int | None = None,
    default: int = 4,
) -> int:
    """Resolve target NSQF level.

    NQR-sourced `course.nsqf_level` takes precedence over demo occupation seed defaults.
    """
    if course_nsqf is not None and course_nsqf > 0:
        return course_nsqf
    if occupation_nsqf is not None and occupation_nsqf > 0:
        return occupation_nsqf
    return default

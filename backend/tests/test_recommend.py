"""Tests for Phase 3 recommendations."""
from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.filters import filter_courses
from app.ml.ranking.ranker import Ranker
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student


def test_hard_constraints_filter():
    student = Student(
        edu_level="10th",
        budget_band="mid",  # max 50,000
        max_duration_months=12
    )

    c1 = Course(id=1, name="Eligible", min_edu="8th", fee_inr=30000, duration_months=6)
    c2 = Course(id=2, name="Too Expensive", min_edu="10th", fee_inr=80000, duration_months=6)
    c3 = Course(id=3, name="Too Long", min_edu="10th", fee_inr=30000, duration_months=24)
    c4 = Course(id=4, name="Edu Too High", min_edu="12th", fee_inr=30000, duration_months=6)

    eligible, rejected = filter_courses(student, [c1, c2, c3, c4])

    assert len(eligible) == 1
    assert eligible[0].id == 1

    assert len(rejected) == 3
    rejected_ids = [r["course"].id for r in rejected]
    assert 2 in rejected_ids
    assert 3 in rejected_ids
    assert 4 in rejected_ids

def test_ranker_fallback():
    ranker = Ranker()
    # Exercise the transparent weighted scorer directly so the assertion holds
    # regardless of whether a trained LightGBM model file happens to be present.
    features1 = {
        "riasec_cosine": 0.9, "aptitude_fit": 0.8, "fee_ratio": 0.5, "retrieval_score": 0.9
    }
    features2 = {
        "riasec_cosine": 0.4, "aptitude_fit": 0.4, "fee_ratio": 1.0, "retrieval_score": 0.4
    }

    score1 = ranker._fallback_score(features1)
    score2 = ranker._fallback_score(features2)

    assert score1 > score2

def test_reason_codes():
    student = Student(edu_level="12th")
    course = Course(fee_inr=15000)
    occupation = Occupation()
    features = {"riasec_cosine": 0.8, "aptitude_fit": 0.9, "fee_ratio": 0.5}
    student_riasec = {"R": 10, "I": 8, "A": 5, "S": 2, "E": 1, "C": 1}

    codes = generate_reason_codes(student, occupation, course, features, student_riasec)
    assert len(codes) >= 2
    code_names = [c["code"] for c in codes]
    assert "INTEREST_MATCH" in code_names
    assert "APTITUDE_STRONG" in code_names
    assert "WITHIN_BUDGET" in code_names

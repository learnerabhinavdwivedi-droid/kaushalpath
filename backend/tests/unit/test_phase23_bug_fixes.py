"""Phase 23 Step 1: Bug fixes and wiring defect regression tests.

Verifies:
a. _salary_percentile deleted; no bogus 'top {pct}%' or 'top 100%' rendered.
b. One budget source in app.core.budget.py; fee_ratio uncapped for explanation;
   WITHIN_BUDGET fires only when fee <= band limit and states that limit;
   exact screenshot case (Fitter, low band).
c. Unified EDU_HIERARCHY and EDU_TO_NSQF in app.core.education.py;
   NQR-sourced courses.nsqf_level takes precedence over demo seed.
d. Retrieval is candidate generation only (top-50 shortlist); score NOT added to ranking;
   free-text work preference passed as stated_interests.
e. Hindi typo in CAREER_MATCH resolved ('उपयुक्तता', not 'उपयुति').
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from app.core.budget import BUDGET_LIMITS
from app.core.education import EDU_HIERARCHY, EDU_TO_NSQF, resolve_course_nsqf
from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking import features, filters
from app.ml.ranking.features import extract_features
from app.ml.ranking.ranker import Ranker
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student
from app.services import recommend_svc


def test_1a_salary_percentile_deleted_and_no_bogus_top_pct():
    """Verify _salary_percentile is removed and 'top {pct}%' is gone from templates."""
    # Ensure _salary_percentile does not exist in recommend_svc
    assert not hasattr(recommend_svc, "_salary_percentile")

    # Read templates and check no template mentions 'top {salary_percentile}%' or 'top {pct}%'
    tpl_path = Path(features.__file__).parent.parent / "explain" / "templates_hi_en.json"
    with open(tpl_path, encoding="utf-8") as f:
        templates = json.load(f)

    for code, tpls in templates.items():
        for lang, text in tpls.items():
            msg = f"Bogus 'top {{...}}%' template in {code}:{lang}: {text}"
            assert "top {" not in text.lower(), msg
            assert "100%" not in text, f"Hardcoded 100% found in {code}:{lang}: {text}"


def test_1b_budget_single_source_and_within_budget_chip():
    """Verify single source of truth for budget and exact screenshot case."""
    # Single source check
    assert filters.BUDGET_LIMITS is BUDGET_LIMITS
    assert features.BUDGET_LIMITS is BUDGET_LIMITS
    assert BUDGET_LIMITS["low"] == 20000.0
    assert BUDGET_LIMITS["mid"] == 60000.0
    assert BUDGET_LIMITS["high"] == float("inf")

    # Screenshot scenario: Learner with low budget band (limit 20,000 INR)
    student_low = Student(
        edu_level="10th",
        budget_band="low",
        state="MH",
        district="Pune",
    )
    occupation_fitter = Occupation(
        id=1,
        name_en="Fitter",
        riasec_r=9.0,
        riasec_i=4.0,
        riasec_a=2.0,
        riasec_s=3.0,
        riasec_e=4.0,
        riasec_c=8.0,
        nsqf_level=3,
        is_vocational=True,
    )
    # Expensive course (fee 25,000 > low limit 20,000)
    course_expensive = Course(
        id=101,
        name="Fitter Trade (Advance)",
        occupation_id=1,
        fee_inr=25000.0,
        min_edu="10th",
        nsqf_level=4,
    )

    # 1. Uncapped fee_ratio in extract_features
    feats_expensive = extract_features(
        student_low,
        occupation_fitter,
        course_expensive,
        student_riasec={"R": 8.0, "I": 4.0, "A": 2.0, "S": 3.0, "E": 4.0, "C": 7.0},
        student_aptitude={"num": 6.0, "mech": 8.0},
    )
    assert feats_expensive["fee_ratio"] == 25000.0 / 20000.0  # 1.25 > 1.0 (uncapped!)

    # 2. WITHIN_BUDGET chip must NOT fire when fee > budget limit
    reasons_exp = generate_reason_codes(
        student_low,
        occupation_fitter,
        course_expensive,
        feats_expensive,
        student_riasec={"R": 8.0, "I": 4.0, "A": 2.0, "S": 3.0, "E": 4.0, "C": 7.0},
        lang="en",
    )
    exp_codes = [r["code"] for r in reasons_exp]
    assert "WITHIN_BUDGET" not in exp_codes, (
        "WITHIN_BUDGET chip fired for fee exceeding budget limit!"
    )

    # 3. Affordable course (fee 15,000 <= low limit 20,000)
    course_affordable = Course(
        id=102,
        name="Fitter Basic Certificate",
        occupation_id=1,
        fee_inr=15000.0,
        min_edu="10th",
        nsqf_level=3,
    )
    feats_affordable = extract_features(
        student_low,
        occupation_fitter,
        course_affordable,
        student_riasec={"R": 8.0, "I": 4.0, "A": 2.0, "S": 3.0, "E": 4.0, "C": 7.0},
        student_aptitude={"num": 6.0, "mech": 8.0},
    )
    assert feats_affordable["fee_ratio"] == 15000.0 / 20000.0  # 0.75 <= 1.0

    reasons_aff = generate_reason_codes(
        student_low,
        occupation_fitter,
        course_affordable,
        feats_affordable,
        student_riasec={"R": 8.0, "I": 4.0, "A": 2.0, "S": 3.0, "E": 4.0, "C": 7.0},
        lang="en",
    )
    aff_codes = [r["code"] for r in reasons_aff]
    assert "WITHIN_BUDGET" in aff_codes
    budget_reason = next(r for r in reasons_aff if r["code"] == "WITHIN_BUDGET")
    assert budget_reason["params"]["limit"] == 20000
    assert "20000" in budget_reason["description"]
    assert "15000" in budget_reason["description"]


def test_1c_education_hierarchy_and_nsqf_precedence():
    """Verify unified education module and NQR course NSQF priority."""
    assert filters.EDU_HIERARCHY is EDU_HIERARCHY
    assert features.EDU_TO_NSQF is EDU_TO_NSQF

    # Course NSQF level must take precedence over occupation NSQF level
    resolved_nsqf = resolve_course_nsqf(course_nsqf=5, occupation_nsqf=3)
    assert resolved_nsqf == 5

    resolved_nsqf_fallback = resolve_course_nsqf(course_nsqf=None, occupation_nsqf=3)
    assert resolved_nsqf_fallback == 3

    # In extract_features, NQR course NSQF takes precedence
    student = Student(edu_level="10th")  # NSQF 3
    occ = Occupation(nsqf_level=2)  # Demo seed level
    course = Course(nsqf_level=5)  # NQR real course level
    feats = extract_features(
        student, occ, course,
        student_riasec={"R": 5.0}, student_aptitude={"num": 5.0},
    )
    # nsqf_gap = |student_nsqf (3) - course_nsqf (5)| / 6.0 = 2/6 = 0.3333
    assert abs(feats["nsqf_gap"] - (2.0 / 6.0)) < 1e-4


def test_1d_retrieval_candidate_generation_only():
    """Verify retrieval score does NOT add to ranking and free-text work preference is passed."""
    ranker = Ranker(use_model=False)

    # Two items with identical features except one has retrieval_score=1.0 and the other 0.0
    f1 = {"riasec_cosine": 0.8, "aptitude_fit": 0.7, "retrieval_score": 1.0}
    f2 = {"riasec_cosine": 0.8, "aptitude_fit": 0.7, "retrieval_score": 0.0}

    s1 = ranker._fallback_score(f1)
    s2 = ranker._fallback_score(f2)
    assert s1 == s2, "Retrieval score contributed to the ranking score!"

    # Test that RecommendService passes work_preference as stated_interests
    mock_db = MagicMock()
    mock_student = Student(
        id=99,
        edu_level="10th",
        budget_band="mid",
        state="MH",
        district="Pune",
        language="en",
    )
    mock_student.work_preference = "automotive repair and welding"
    mock_db.get.return_value = mock_student

    # Assessment mock
    mock_assessment = MagicMock()
    mock_assessment.riasec_r = 8.0
    mock_assessment.riasec_i = 4.0
    mock_assessment.riasec_a = 2.0
    mock_assessment.riasec_s = 3.0
    mock_assessment.riasec_e = 4.0
    mock_assessment.riasec_c = 7.0
    mock_assessment.apt_num = 6.0
    mock_assessment.apt_verbal = 5.0
    mock_assessment.apt_spatial = 7.0
    mock_assessment.apt_mech = 8.0

    mock_course = Course(
        id=1, name="Auto Mechanic", occupation_id=1, min_edu="8th", fee_inr=10000.0
    )
    mock_db.scalar.return_value = mock_assessment
    mock_db.scalars.return_value.all.return_value = [mock_course]

    svc = recommend_svc.RecommendService(mock_db)
    svc._centres_by_course = MagicMock(return_value={})
    svc._markets_by_occ = MagicMock(return_value={})
    svc._abilities_by_occ = MagicMock(return_value={})
    svc.searcher = MagicMock()
    svc.searcher.search.return_value = []

    svc.get_recommendations(student_id=99, top_k=3)
    svc.searcher.search.assert_called_once()
    call_kwargs = svc.searcher.search.call_args.kwargs
    assert call_kwargs["stated_interests"] == "automotive repair and welding"


def test_1e_hindi_typo_fixed_in_career_match():
    """Verify Hindi template for CAREER_MATCH has 'उपयुक्तता' and not 'उपयुति'."""
    tpl_path = Path(features.__file__).parent.parent / "explain" / "templates_hi_en.json"
    with open(tpl_path, encoding="utf-8") as f:
        templates = json.load(f)

    hi_text = templates["CAREER_MATCH"]["hi"]
    assert "उपयुक्तता" in hi_text, f"Expected 'उपयुक्तता' in Hindi CAREER_MATCH, got: {hi_text}"
    assert "उपयुति" not in hi_text, f"Found typo 'उपयुति' in Hindi CAREER_MATCH: {hi_text}"

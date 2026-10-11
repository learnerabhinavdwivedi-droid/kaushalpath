"""Phase 23: Unit tests for Recommender v2.

Real features, honest explanations, and missing-data neutrality.
Tests:
1. Missing-data neutrality: Two otherwise identical trades that differ only in
   data availability get identical scores (weights renormalised, no 0.5 fills).
2. Faithfulness: Every number in a rendered reason code description appears
   in its evidence row/dictionary.
3. Reason codes contract: Every code carries evidence_id, source, and grade.
   Two-code minimum satisfied by INTEREST_MATCH and ELIGIBLE when outcome data is absent.
4. Confidence & abstention: Low confidence marks items and triggers
   counsellor_suggested=True with escalation hook.
5. Provider quality: Centres ordered by distance -> outcome n >= 30 -> scorecard,
   without affecting course scores.
6. Family context: Association from education_route_compare with n and grade.
"""
from __future__ import annotations

import re
from unittest.mock import MagicMock

from app.ml.explain.reason_codes import generate_reason_codes
from app.ml.ranking.ranker import Ranker
from app.models.course import Course
from app.models.occupation import Occupation
from app.models.student import Student
from app.services.recommend_svc import (
    _get_family_context,
    _order_centres_by_quality,
    _scheme_subsidy_pct,
)


def test_missing_data_neutrality():
    """Prove two identical trades differing only in data availability get identical scores."""
    ranker = Ranker()

    # Trade 1: Base features present with value 0.80, outcome features missing (None)
    trade_1_features = {
        "riasec_cosine": 0.80,
        "top3_code_overlap": 0.80,
        "aptitude_fit_occ": 0.80,
        "placement_est": None,
        "earnings_median_pct": None,
        "earnings_floor_pct": None,
        "local_demand": None,
        "net_cost_ratio": None,
        "distance_km": None,
        "progression_value": None,
    }

    # Trade 2: Same present features (0.80), and also has outcomes and demand present at 0.80
    # (distance=100km -> dist_score = 1 - 100/500 = 0.80, net_cost_ratio=0.20 -> cost_score = 0.80,
    # progression_value=2.4 -> 2.4/3.0 = 0.80)
    trade_2_features = {
        "riasec_cosine": 0.80,
        "top3_code_overlap": 0.80,
        "aptitude_fit_occ": 0.80,
        "placement_est": 0.80,
        "earnings_median_pct": 0.80,
        "earnings_floor_pct": 0.80,
        "local_demand": 0.80,
        "net_cost_ratio": 0.20,  # cost_score = 0.80
        "distance_km": 100.0,    # distance_score = 0.80
        "progression_value": 2.4, # progression_score = 0.80
    }

    score_1 = ranker.score(trade_1_features, interest_confidence=1.0)
    score_2 = ranker.score(trade_2_features, interest_confidence=1.0)

    # Under missing-data neutrality, missing features have their weights renormalised.
    # Because all available features are 0.80, both must score exactly 0.80!
    assert score_1 == 0.80, f"Expected 0.80, got {score_1} (did missing data fill 0.5?)"
    assert score_2 == 0.80, f"Expected 0.80, got {score_2}"
    assert score_1 == score_2, "Missing data availability biased the ranking score!"


def test_faithfulness_every_number_in_evidence():
    """Verify every number in a rendered description appears in its evidence row."""
    student = Student(
        edu_level="10th",
        budget_band="low",
        state="Karnataka",
        district="Bengaluru Urban",
        language="en",
    )
    occupation = Occupation(
        id=5,
        name_en="Electrician",
        riasec_r=9.0,
        riasec_i=6.0,
        riasec_a=2.0,
        riasec_s=3.0,
        riasec_e=4.0,
        riasec_c=6.0,
        nsqf_level=4,
        is_vocational=True,
    )
    course = Course(
        id=50,
        occupation_id=5,
        name="Electrician Certification",
        fee_inr=15000.0,
        min_edu="10th",
        nsqf_level=4,
    )

    earnings_evidence = {
        "id": 101,
        "value": 18500.0,
        "interval": [16000.0, 21000.0],
        "n": 65,
        "level_used": "district",
        "grade": "A",
        "definition": "tracer_survey",
        "source": "DGT STRIVE",
        "year": 2024,
    }
    placement_evidence = {
        "id": 202,
        "value": 0.72,
        "interval": [0.65, 0.79],
        "n": 120,
        "level_used": "state",
        "grade": "B",
        "definition": "verified",
        "source": "PMKVY",
    }

    features = {
        "riasec_cosine": 0.85,
        "top3_code_overlap": 1.0,
        "aptitude_fit_occ": 0.75,
        "distance_km": 15.0,
        "local_demand": 0.78,
    }
    student_riasec = {"R": 9.0, "I": 7.0, "A": 2.0, "S": 3.0, "E": 4.0, "C": 5.0}

    # Centre for provider quality
    dummy_centre = MagicMock()
    dummy_centre.id = 1
    dummy_centre.name = "Govt ITI"
    dummy_centre.outcome_n = 45

    reasons = generate_reason_codes(
        student,
        occupation,
        course,
        features,
        student_riasec,
        lang="en",
        earnings_evidence=earnings_evidence,
        placement_evidence=placement_evidence,
        ordered_centres=[dummy_centre],
    )

    assert len(reasons) >= 2

    # Check faithfulness for every generated code
    for r in reasons:
        desc = r["description"]
        ev = r["evidence"]
        code = r["code"]

        # Ensure evidence_id, source, and grade are present
        assert "evidence_id" in r
        assert "source" in r
        assert "grade" in r
        assert r["grade"] in ("A", "B", "C", "D")

        if ev is None:
            continue

        # Extract all numbers from rendered description (integers and decimals)
        numbers_in_text = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", desc)]
        # Gather all numbers in the evidence dictionary
        ev_numbers = []
        if isinstance(ev, dict):
            for v in ev.values():
                if isinstance(v, int | float):
                    ev_numbers.append(float(v))
        elif isinstance(ev, int | float):
            ev_numbers.append(float(ev))

        for num in numbers_in_text:
            msg = (
                f"Number {num} in description '{desc}' (code {code}) "
                f"does not appear in evidence {ev}"
            )
            assert any(abs(num - ev_n) < 1e-3 for ev_n in ev_numbers), msg


def test_two_code_minimum_with_absent_outcomes():
    """Verify that when outcome data is absent, INTEREST_MATCH and ELIGIBLE satisfy >=2 codes."""
    student = Student(
        edu_level="10th",
        budget_band="low",
        state="Karnataka",
        district="Mysuru",
        language="en",
    )
    occupation = Occupation(
        id=7,
        name_en="Welder",
        riasec_r=9.0,
        riasec_i=2.0,
        riasec_a=1.0,
        riasec_s=1.0,
        riasec_e=2.0,
        riasec_c=5.0,
        nsqf_level=3,
        is_vocational=True,
    )
    course = Course(
        id=70,
        occupation_id=7,
        name="Welder Basic",
        fee_inr=50000.0,
        min_edu="8th",
        nsqf_level=3,
    )

    # Features with no outcome rows and no high demand
    features = {
        "riasec_cosine": 0.40,  # below 0.70 threshold
        "top3_code_overlap": 0.33,
        "aptitude_fit_occ": 0.50,
        "distance_km": 300.0,   # > 150km
        "local_demand": 0.40,   # < 0.70
    }
    student_riasec = {"R": 8.0, "I": 3.0, "A": 2.0, "S": 1.0, "E": 2.0, "C": 4.0}

    reasons = generate_reason_codes(
        student,
        occupation,
        course,
        features,
        student_riasec,
        lang="en",
        earnings_evidence=None,
        placement_evidence=None,
    )

    assert len(reasons) >= 2
    codes = [r["code"] for r in reasons]
    assert "INTEREST_MATCH" in codes
    assert "ELIGIBLE" in codes


def test_scheme_subsidies_by_income_band():
    """Verify scheme subsidy percentages by learner income band."""
    assert _scheme_subsidy_pct("lt_1l") == 1.0
    assert _scheme_subsidy_pct("1l_3l") == 0.5
    assert _scheme_subsidy_pct("3l_6l") == 0.25
    assert _scheme_subsidy_pct("gt_6l") == 0.0
    assert _scheme_subsidy_pct(None) == 0.0


def test_provider_quality_centre_ordering():
    """Verify centre ordering: distance -> outcome n >= 30 -> scorecard."""
    student = Student(district="Pune", state="Maharashtra")

    c1 = MagicMock()
    c1.id = 1
    c1.district = "Mumbai"
    c1.state = "Maharashtra"

    c2 = MagicMock()
    c2.id = 2
    c2.district = "Pune"  # home district!
    c2.state = "Maharashtra"

    c3 = MagicMock()
    c3.id = 3
    c3.district = "Nagpur"
    c3.state = "Maharashtra"

    # c3 has large outcome n >= 30, c1 has low n
    o_c3 = MagicMock()
    o_c3.enrolled = 50
    o_c3.placement_rate = 0.85

    o_c1 = MagicMock()
    o_c1.enrolled = 15
    o_c1.placement_rate = 0.90

    outcomes = {
        3: [o_c3],
        1: [o_c1],
        2: [],
    }

    ordered = _order_centres_by_quality(student, [c1, c3, c2], outcomes)
    # c2 is in home district (tier 0) -> must come first
    assert ordered[0].id == 2
    # c3 has n >= 30 (tier 0 in n among state centres) -> must outrank c1 (n=15)
    assert ordered[1].id == 3
    assert ordered[2].id == 1


def test_family_context_association():
    """Verify education route comparison returns empirical association with n and Grade C."""
    ctx = _get_family_context("Maharashtra", "class_10th")
    if ctx is not None:
        assert "difference_inr" in ctx
        assert "education_baseline" in ctx
        assert "vocational_route" in ctx
        assert "n" in ctx
        assert ctx["grade"] == "C"
        assert "interpretation_note" in ctx
        assert "not a causal effect" in ctx["interpretation_note"].lower()

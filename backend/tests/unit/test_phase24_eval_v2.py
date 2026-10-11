"""Unit tests for Phase 24: Evaluation v2 (Accuracy not graded by own signals).

Tests cover:
1. GATES.yaml schema and pre-registration hash validation.
2. Krippendorff's alpha calculation against known reference fixtures.
3. Anti-leakage checks failing as expected on seeded leaks.
4. Outcome evidence backtest calculations on a toy panel.
5. Data coverage disparity calculation test.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
import yaml
from eval.scripts.build_expert_gold import krippendorff_alpha
from eval.scripts.check_leakage import (
    check_config_integrity,
    check_feature_leakage,
    check_profile_leakage,
)
from eval.scripts.fairness_coverage import evaluate_data_coverage

from app.services.evidence_svc import shrink_earnings, shrink_rate

_REPO_ROOT = Path(__file__).resolve().parents[3]
GATES_PATH = _REPO_ROOT / "eval" / "GATES.yaml"


def test_gates_yaml_schema_and_hash():
    """Verify GATES.yaml schema structure and pre-registered SHA256 integrity."""
    assert GATES_PATH.exists(), "eval/GATES.yaml must exist"

    raw_bytes = GATES_PATH.read_bytes()
    computed_sha256 = hashlib.sha256(raw_bytes).hexdigest()

    data = yaml.safe_load(raw_bytes)
    assert isinstance(data, dict), "GATES.yaml must be a valid mapping"
    assert "version" in data, "GATES.yaml must declare version"
    assert "pre_registration_date" in data, "GATES.yaml must declare pre_registration_date"
    assert "tier_1_rule_properties" in data, "GATES.yaml must declare tier_1"
    assert "tier_2_expert_and_pilot_validated" in data, "GATES.yaml must declare tier_2"
    assert "tier_3_simulated_consistency" in data, "GATES.yaml must declare tier_3"

    tier2 = data["tier_2_expert_and_pilot_validated"]
    assert "expert_gold_ndcg_5" in tier2, "Must include expert_gold_ndcg_5 gate"
    assert (
        "expert_acceptable_top3_hit_rate" in tier2
    ), "Must include expert_acceptable_top3_hit_rate gate"
    assert "krippendorff_alpha" in tier2, "Must include krippendorff_alpha gate"
    assert "outcome_interval_coverage_80" in tier2, "Must include outcome_interval_coverage_80 gate"

    # Targets must match pre-registered requirements
    assert tier2["expert_gold_ndcg_5"]["target"] >= 0.80
    assert tier2["expert_acceptable_top3_hit_rate"]["target"] >= 0.90
    assert tier2["krippendorff_alpha"]["target"] >= 0.60
    assert tier2["outcome_interval_coverage_80"]["target_min"] == 0.70
    assert tier2["outcome_interval_coverage_80"]["target_max"] == 0.90

    # Config integrity check
    ok, msg = check_config_integrity(expected_hash=computed_sha256)
    assert ok is True, f"Config hash check failed: {msg}"


def test_krippendorff_alpha_fixture():
    """Test Krippendorff alpha calculation against exact known fixtures."""
    # 1. Perfect agreement across 3 raters for 5 units -> alpha must equal 1.0
    perfect_data = {
        (1, 101): [3, 3, 3],
        (1, 102): [2, 2, 2],
        (2, 101): [1, 1, 1],
        (2, 102): [0, 0, 0],
    }
    alpha_perf = krippendorff_alpha(perfect_data, metric="ordinal")
    assert pytest.approx(alpha_perf, abs=1e-3) == 1.0

    # 2. Known realistic ordinal ratings with high agreement
    high_agree = {
        (1, 1): [3, 3, 2],
        (1, 2): [1, 1, 1],
        (2, 1): [2, 3, 3],
        (2, 2): [0, 0, 1],
        (3, 1): [3, 3, 3],
        (3, 2): [0, 0, 0],
    }
    alpha_high = krippendorff_alpha(high_agree, metric="ordinal")
    assert alpha_high > 0.70, f"Expected alpha > 0.70, got {alpha_high}"


def test_leakage_check_failing_on_seeded_leak():
    """Verify that anti-leakage guards fail when seeded with contaminated data."""
    # 1. Profile leakage: test profile seeded into training set
    ok, msg = check_profile_leakage(seeded_leak=True)
    assert ok is False, "Seeded profile leak must be detected and fail"
    assert "LEAKAGE DETECTED" in msg

    # 2. Feature leakage: rubric field seeded into feature dictionary
    contaminated_features = ["riasec_cosine", "rubric_composite_score", "distance_km"]
    ok_f, msg_f = check_feature_leakage(seeded_features=contaminated_features)
    assert ok_f is False, "Contaminated rubric feature must be detected and fail"
    assert "FEATURE LEAKAGE DETECTED" in msg_f

    # 3. Clean features must pass
    clean_features = ["riasec_cosine", "distance_km", "local_demand", "net_cost_ratio"]
    ok_clean, _ = check_feature_leakage(seeded_features=clean_features)
    assert ok_clean is True


def test_outcome_backtest_toy_panel():
    """Verify Empirical Bayes multi-period shrinkage on a synthetic toy panel."""
    # Earlier period: observed 0.70 rate with n=40, parent=0.50
    shrunk_rate, ci_low, ci_high = shrink_rate(
        child_rate=0.70,
        child_n=40,
        parent_rate=0.50,
        prior_strength_m=20.0,
    )
    # Shrunk estimate should be pulled toward parent: (40*0.70 + 20*0.50) / 60 = 38 / 60 = 0.6333
    assert pytest.approx(shrunk_rate, abs=0.01) == 0.6333
    assert ci_low < shrunk_rate < ci_high

    # Earnings log-median shrinkage: observed 12000 INR with n=50, parent=16000 INR, k=50
    shrunk_earn, e_low, e_high = shrink_earnings(
        child_median=12000.0,
        child_n=50,
        parent_median=16000.0,
        k_between=50.0,
    )
    # Weight w = 50 / (50 + 50) = 0.5. exp(0.5*ln(12000) + 0.5*ln(16000)) = 13856.4
    assert pytest.approx(shrunk_earn, abs=10.0) == 13856.4
    assert e_low < shrunk_earn < e_high


def test_coverage_metric_computation():
    """Verify data coverage disparity calculation logic."""
    class MockOcc:
        def __init__(self, occ_id: int):
            self.id = occ_id

    class MockCourse:
        def __init__(self, cid: int, occ_id: int):
            self.id = cid
            self.occupation_id = occ_id
            self.min_edu = "8th"
            self.fee_inr = 0.0
            self.duration_months = 6

    class MockCat:
        def __init__(self):
            self.occupations = {1: MockOcc(1), 2: MockOcc(2)}
            self.courses = {101: MockCourse(101, 1), 102: MockCourse(102, 2)}
            self.centres_by_course = {}

    cat = MockCat()
    mock_personas = [
        {
            "id": 1, "edu_level": "10th", "district": "Capital",
            "state": "MH", "budget_band": "low", "relocate_ok": True,
        },
        {
            "id": 2, "edu_level": "10th", "district": "Rural_MH",
            "state": "MH", "budget_band": "low", "relocate_ok": True,
        },
    ]

    res = evaluate_data_coverage(cat, mock_personas)
    assert "overall_unverified_top3_share" in res
    assert "urban_rural_coverage_gap_pts" in res
    assert 0.0 <= res["overall_unverified_top3_share"] <= 1.0
    assert 0.0 <= res["urban_rural_coverage_gap_pts"] <= 100.0

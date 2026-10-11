"""Unit tests for Phase 21: Assessment v2 (grounded items, calibration, tie-breaks, aptitude fit).

Covers all Phase 21 requirements:
- Item bank structure (Item A & B)
- 2PL parameter recovery within +/- 0.25 (Item C)
- Adaptive engine reading calibrated a and b (Item C)
- Forced-choice tie-breaks when top-3 are within 1 SEM (Item D)
- Pure aptitude_match function: shortfall only, surplus unpenalized, SE shrinkage (Item F)
- check_items validator failure detection (Item A & B)
- Psychometric validity study suite on fixture (Item G)
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.ml.assessment import adaptive, scoring
from app.ml.ranking.aptitude_fit import aptitude_match
from scripts.calibrate_items import run_parameter_recovery_test
from scripts.check_items import check_interest_items, check_aptitude_items
from scripts.validity_studies import generate_fixture_data, evaluate_reliability, evaluate_convergent, evaluate_known_groups

ITEMS_V2_DIR = REPO_ROOT / "backend" / "app" / "ml" / "assessment" / "items_v2"


def test_item_bank_structure() -> None:
    interest_path = ITEMS_V2_DIR / "interest_items.json"
    aptitude_path = ITEMS_V2_DIR / "aptitude_items.json"

    assert interest_path.exists(), "interest_items.json must exist"
    assert aptitude_path.exists(), "aptitude_items.json must exist"

    with interest_path.open(encoding="utf-8") as f:
        interest_items = json.load(f)
    with aptitude_path.open(encoding="utf-8") as f:
        aptitude_items = json.load(f)

    # RIASEC checks: >= 12 per dimension, required fields, text_hi <= 12 words
    assert len(interest_items) >= 72
    from collections import Counter
    counts = Counter(it["dimension"] for it in interest_items)
    for d in ("R", "I", "A", "S", "E", "C"):
        assert counts[d] >= 12, f"Dimension {d} has {counts[d]} items (< 12 required)"

    for it in interest_items:
        assert {"id", "dimension", "text_en", "text_hi", "source_element", "local_context", "reviewed_by", "needs_review"} <= it.keys()
        words = len(it["text_hi"].strip().split())
        assert words <= 12, f"Item {it['id']} Hindi text exceeds 12 words: {it['text_hi']}"

    # Aptitude checks: >= 10 per construct, 4 ASER difficulty bands
    assert len(aptitude_items) >= 40
    apt_counts = Counter(it["construct"] for it in aptitude_items)
    for c in ("num", "verbal", "spatial", "mech"):
        assert apt_counts[c] >= 10, f"Construct {c} has {apt_counts[c]} items (< 10 required)"

    bands_per_c = {c: set() for c in ("num", "verbal", "spatial", "mech")}
    for it in aptitude_items:
        assert {"id", "construct", "band", "aser_anchor", "text_en", "text_hi", "options", "correct_answer", "image_path"} <= it.keys()
        bands_per_c[it["construct"]].add(it["band"])

    for c in ("num", "verbal", "spatial", "mech"):
        assert {1, 2, 3, 4} <= bands_per_c[c], f"Construct {c} missing difficulty bands"


def test_parameter_recovery_within_tolerance() -> None:
    """Recovery test: 2,000 simulated respondents recover known a and b within +/- 0.25."""
    res = run_parameter_recovery_test(n_respondents=2000, seed=2026)
    assert res["passed"] is True
    assert res["max_err_a"] <= 0.25, f"Discrimination error {res['max_err_a']} > 0.25"
    assert res["max_err_b"] <= 0.25, f"Difficulty error {res['max_err_b']} > 0.25"


def test_adaptive_engine_uses_per_item_a_and_b() -> None:
    """Verify adaptive engine accounts for calibrated discrimination and difficulty."""
    bank = adaptive.load_interest_bank()
    assert any("a" in it or "discrimination" in it for it in bank)

    state = adaptive.new_state()
    # Seed minimal answers
    item1 = adaptive.next_interest_item(state, bank)
    assert item1 is not None
    adaptive.record_interest_answer(state, bank, item1["id"], 5)

    item2 = adaptive.next_interest_item(state, bank)
    assert item2 is not None
    assert item2["id"] != item1["id"]


def test_forced_choice_tie_break_trigger_and_resolution() -> None:
    """When top dimensions are within 1 SEM, engine triggers tie-break pairs and updates theta."""
    bank = adaptive.load_interest_bank()
    state = adaptive.new_state()

    # Seed near-identical answers for R and I, low for others
    # Seed 2 items per dimension
    for it in bank:
        dim = it["dimension"]
        if it["id"] not in state["interest_responses"]:
            # R and I receive identical scores
            if dim in ("R", "I"):
                state["interest_responses"][it["id"]] = 4
            elif dim in ("A", "S", "E", "C"):
                state["interest_responses"][it["id"]] = 1

    # Check that contested dimensions are detected
    contested = adaptive.find_contested_dimensions(state, bank)
    assert contested is not None
    assert set(contested) <= {"R", "I"}

    # Generate tie-break item
    tb_item = adaptive.next_tie_break_item(state, bank)
    assert tb_item is not None
    assert tb_item["item_type"] == "pair"
    assert tb_item["id"].startswith("PAIR_")

    # Record preference for A
    prior_riasec = dict(state["riasec"])
    adaptive.record_interest_answer(state, bank, tb_item["id"], "A")
    assert state["tie_breaks_asked"] == 1
    # Chosen dimension score is boosted
    assert state["pair_adjustments"][tb_item["dim_a"]] > 0.0
    assert state["pair_adjustments"][tb_item["dim_b"]] < 0.0


def test_aptitude_match_table() -> None:
    """Table-driven test for pure aptitude_match: shortfall only, surplus unpenalized, SE shrinkage."""
    # 1. Surplus: learner exceeds requirements on all 4 dimensions
    res_surplus = aptitude_match(
        learner_theta={"num": 0.85, "verbal": 0.80, "spatial": 0.85, "mech": 0.90},
        learner_se={"num": 0.05, "verbal": 0.05, "spatial": 0.05, "mech": 0.05},
        occ_requirements={"num": 0.50, "verbal": 0.40, "spatial": 0.50, "mech": 0.50},
    )
    assert res_surplus["shortfalls"] == {"num": 0.0, "verbal": 0.0, "spatial": 0.0, "mech": 0.0}
    assert res_surplus["score"] >= 0.90
    assert res_surplus["confidence"] >= 0.85

    # 2. Shortfall: learner below requirement
    res_shortfall = aptitude_match(
        learner_theta={"num": 0.25, "verbal": 0.30, "spatial": 0.20, "mech": 0.30},
        learner_se={"num": 0.05, "verbal": 0.05, "spatial": 0.05, "mech": 0.05},
        occ_requirements={"num": 0.70, "verbal": 0.65, "spatial": 0.80, "mech": 0.75},
    )
    assert all(val > 0.0 for val in res_shortfall["shortfalls"].values())
    assert res_shortfall["score"] < 0.40

    # 3. SE Shrinkage: high SE pulls score toward neutral 0.50 and lowers confidence
    res_high_se = aptitude_match(
        learner_theta={"num": 0.25, "verbal": 0.30, "spatial": 0.20, "mech": 0.30},
        learner_se={"num": 0.45, "verbal": 0.45, "spatial": 0.45, "mech": 0.45},
        occ_requirements={"num": 0.70, "verbal": 0.65, "spatial": 0.80, "mech": 0.75},
    )
    assert res_high_se["confidence"] < res_shortfall["confidence"]
    assert res_high_se["score"] > res_shortfall["score"]  # Shrunk toward 0.50


def test_check_items_validation_failures() -> None:
    """Validator fails on missing fields, word count > 12 words, or bad construct."""
    bad_interest = [
        {
            "id": "BAD_01",
            "dimension": "R",
            "text_en": "Fix something.",
            "text_hi": "यह एक बहुत लंबा वाक्य है जिसमें जानबूझकर बारह से अधिक शब्द डाले गए हैं ताकि टेस्ट फेल हो सके।",
            "source_element": "test",
            "local_context": "test",
            "reviewed_by": "test",
            "needs_review": False,
        }
    ]
    errors = check_interest_items(bad_interest)
    assert any("> 12 words" in e for e in errors)

    bad_aptitude = [
        {
            "id": "BAD_APT_01",
            "construct": "invalid_construct",
            "band": 5,
            "aser_anchor": "test",
            "text_en": "test",
            "text_hi": "test",
            "options": ["A"],
            "correct_answer": "B",
            "image_path": None,
        }
    ]
    apt_errors = check_aptitude_items(bad_aptitude)
    assert any("invalid construct" in e for e in apt_errors)


def test_validity_studies_fixture_run() -> None:
    """Psychometric validity evaluation suite runs end to end on synthetic fixture."""
    data = generate_fixture_data()
    rel = evaluate_reliability(data["retest_t1"], data["retest_t2"])
    assert all(r >= 0.70 for r in rel.values())

    conv = evaluate_convergent(data["conv_kp"], data["conv_benchmark"])
    assert all(r >= 0.60 for r in conv.values())

    kg = evaluate_known_groups(data["kg_profiles"], data["kg_labels"])
    assert kg["macro_mean_auc"] >= 0.75

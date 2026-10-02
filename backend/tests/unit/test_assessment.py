"""Phase 2 assessment-engine tests.

Covers the PHASE_2.md TESTS list: update rule, stop rule, resumability, and a
property check that every score stays in [0,1]. Item-bank integrity (>=60
interest items, aptitude coverage) is asserted too. The adaptive engine is pure
and DB-free, so these are fast unit tests; the HTTP wiring is exercised
separately in tests/integration/test_assessment_api.py.
"""
from __future__ import annotations

import json
import random

import pytest

from app.ml.assessment import adaptive, scoring, scoring_full

RIASEC_DIMS = scoring.RIASEC_DIMS
APTITUDE_DIMS = scoring.APTITUDE_DIMS


@pytest.fixture(scope="module")
def bank() -> list[dict]:
    return adaptive.load_interest_bank()


@pytest.fixture(scope="module")
def aptitude_bank() -> list[dict]:
    return adaptive.load_aptitude_bank()


def _persona_response(latent: dict[str, float], item: dict) -> int:
    """Deterministic (noise-free) 1..5 answer for a latent persona."""
    signed = 2.0 * latent.get(item["dimension"], 0.5) - 1.0
    if item.get("reverse", False):
        signed = -signed
    return max(1, min(5, round(signed * 2 + 3)))


def _run_adaptive(latent: dict[str, float], bank: list[dict]) -> tuple[dict, int]:
    """Drive the interest section to completion; return (final_state, items)."""
    state = adaptive.new_state()
    asked = 0
    while True:
        item = adaptive.next_interest_item(state, bank)
        if item is None or adaptive.is_interest_complete(state, bank):
            break
        adaptive.record_interest_answer(state, bank, item["id"], _persona_response(latent, item))
        asked += 1
    return state, asked


# --- update rule -------------------------------------------------------------
def test_update_rule_single_answer(bank: list[dict]) -> None:
    """A single positive answer moves its own dimension off the 0.5 midpoint."""
    state = adaptive.new_state()
    item = adaptive.next_interest_item(state, bank)
    assert item is not None
    dim = item["dimension"]
    adaptive.record_interest_answer(state, bank, item["id"], 5)
    assert state["interest_responses"][item["id"]] == 5
    assert state["riasec"][dim] > 0.5
    assert 0.0 <= state["riasec"][dim] <= 1.0
    assert state["items_answered"] == 1


def test_update_rule_reverse_item_flips(bank: list[dict]) -> None:
    reverse = next(it for it in bank if it.get("reverse"))
    forward = next(it for it in bank if not it.get("reverse"))
    assert scoring.signed(5, reverse["reverse"]) == -1.0
    assert scoring.signed(5, forward["reverse"]) == 1.0


def test_answer_idempotent_and_validates_range(bank: list[dict]) -> None:
    state = adaptive.new_state()
    item = adaptive.next_interest_item(state, bank)
    adaptive.record_interest_answer(state, bank, item["id"], 4)
    adaptive.record_interest_answer(state, bank, item["id"], 1)  # replayed -> ignored
    assert state["interest_responses"][item["id"]] == 4
    with pytest.raises(ValueError):
        adaptive.record_interest_answer(state, bank, "ZZZ", 3)
    with pytest.raises(ValueError):  # out-of-range on a fresh item is rejected
        adaptive.record_interest_answer(state, bank, "R01", 9)


# --- stop rule ---------------------------------------------------------------
def test_stop_rule_early_on_confidence(bank: list[dict]) -> None:
    """A persona with a clear top-3 stops before the 24-item target.

    Ranks 4-6 tie (I=C=2) but the Holland code ignores them, so the stop rule
    still fires — this is the regression guard for the order-relevant-boundary
    fix in ``ordering_confidence``.
    """
    latent = {"R": 0.95, "E": 0.8, "A": 0.55, "I": 0.3, "S": 0.05, "C": 0.3}
    state, asked = _run_adaptive(latent, bank)
    assert adaptive.is_interest_complete(state, bank)
    assert state["confidence"] >= adaptive.CONF_STOP
    assert asked < adaptive.TARGET_ITEMS
    assert state["top3_code"] == "REA"


def test_genuine_tie_does_not_stop_early(bank: list[dict]) -> None:
    """A real top-3 tie (two dims at Likert 5) is unresolvable -> run to target."""
    latent = {"R": 0.9, "E": 0.9, "A": 0.5, "I": 0.5, "S": 0.1, "C": 0.1}
    state, asked = _run_adaptive(latent, bank)
    assert state["confidence"] < adaptive.CONF_STOP
    assert asked == adaptive.TARGET_ITEMS  # stopped on target, not confidence


def test_stop_rule_hard_cap(bank: list[dict]) -> None:
    state = adaptive.new_state()
    for item in bank[: adaptive.HARD_CAP]:
        state["interest_responses"][item["id"]] = 3
    adaptive._recompute(state, bank, None)
    assert adaptive.is_interest_complete(state, bank)


def test_never_exceeds_hard_cap(bank: list[dict]) -> None:
    rng = random.Random(7)
    latent = {d: rng.random() for d in RIASEC_DIMS}
    _, asked = _run_adaptive(latent, bank)
    assert asked <= adaptive.HARD_CAP


# --- property: scores bounded ------------------------------------------------
def test_scores_stay_in_unit_interval(bank: list[dict], aptitude_bank: list[dict]) -> None:
    rng = random.Random(42)
    for _ in range(50):
        state = adaptive.new_state()
        for item in bank:
            if rng.random() < 0.6:
                state["interest_responses"][item["id"]] = rng.randint(1, 5)
            if rng.random() < 0.5:
                state["aptitude_responses"][item["id"]] = rng.random() < 0.5
        scores = scoring.interest_scores(state["interest_responses"], bank)
        assert all(0.0 <= v <= 1.0 for v in scores.values())
        apt = scoring.aptitude_scores(state["aptitude_responses"], aptitude_bank)
        assert all(0.0 <= v <= 1.0 for v in apt.values())
        code = scoring.top3_code(scores)
        assert len(set(code)) == 3 and all(c in RIASEC_DIMS for c in code)


# --- resumability ------------------------------------------------------------
def test_resumability_via_json(bank: list[dict]) -> None:
    state = adaptive.new_state()
    for _ in range(6):
        item = adaptive.next_interest_item(state, bank)
        adaptive.record_interest_answer(state, bank, item["id"], 4)
    restored = json.loads(json.dumps(state))
    assert adaptive.next_interest_item(restored, bank)["id"] == adaptive.next_interest_item(
        state, bank
    )["id"]
    assert restored["riasec"] == state["riasec"]
    assert abs(adaptive.ordering_confidence(restored, bank) - state["confidence"]) < 1e-9


# --- item bank integrity -----------------------------------------------------
def test_interest_bank_meets_spec(bank: list[dict]) -> None:
    assert len(bank) >= 60
    ids = {it["id"] for it in bank}
    assert len(ids) == len(bank), "item ids must be unique"
    from collections import Counter

    counts = Counter(it["dimension"] for it in bank)
    for dim in RIASEC_DIMS:
        assert counts[dim] >= 6, f"dimension {dim} has too few items"
    for it in bank:
        assert {"id", "text_en", "text_hi", "dimension", "reverse", "difficulty"} <= it.keys()
        assert 0.0 <= it["difficulty"] <= 1.0


def test_aptitude_bank_five_per_dim(aptitude_bank: list[dict]) -> None:
    from collections import Counter

    assert len(aptitude_bank) == 20
    counts = Counter(it["dimension"] for it in aptitude_bank)
    for dim in APTITUDE_DIMS:
        assert counts[dim] == 5
    for it in aptitude_bank:
        assert it["answer"] in it["options"]


# --- reference scorer --------------------------------------------------------
def test_reference_top3_reproduces_personas(bank: list[dict]) -> None:
    latent = {"R": 0.95, "E": 0.9, "C": 0.85, "I": 0.2, "A": 0.15, "S": 0.1}
    ref = scoring_full.reference_top3(latent, bank, seed=1)
    assert set(ref) == {"R", "E", "C"}

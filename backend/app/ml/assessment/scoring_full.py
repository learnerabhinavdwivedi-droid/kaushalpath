"""Reference *full-test* scorer (the ground truth for the G4 metric).

The adaptive engine stops early (target <=24 items). To judge whether it got
the *same* answer a full inventory would, we score a synthetic respondent over
the **entire** RIASEC bank and take that top-3 code as the reference. G4 is the
share of simulated respondents whose adaptive top-3 matches this reference.

This is a per-respondent helper. The end-to-end replay (personas -> adaptive
run -> G4 + avg items) lives in `eval/scripts/sim_assessment.py`.
"""
from __future__ import annotations

import random
from typing import Any

from app.ml.assessment import adaptive, scoring


def _to_signed(score_01: float) -> float:
    """Map a latent [0,1] persona score onto the signed [-1,1] response scale."""
    return max(-1.0, min(1.0, 2.0 * score_01 - 1.0))


def full_bank_responses(
    persona_latent: dict[str, float],
    bank: list[dict],
    rng: random.Random,
    noise: float = 0.15,
) -> dict[str, int]:
    """Sample a 1..5 answer for *every* item, centred on the persona's latent.

    A reverse-scored item flips the persona's affinity so a high-R person
    *disagrees* with "I prefer to stay quiet" style items. Responses cluster on
    the latent with small noise — this models a consistent respondent, not real
    survey data (see the docstring in the simulation script).
    """
    responses: dict[str, int] = {}
    for item in bank:
        signed = _to_signed(persona_latent.get(item["dimension"], 0.5))
        if item.get("reverse", False):
            signed = -signed
        noisy = max(-1.0, min(1.0, rng.gauss(signed, noise)))
        # signed [-1,1] -> Likert 1..5
        value = round(noisy * 2 + 3)
        responses[item["id"]] = max(1, min(5, value))
    return responses


def full_scores(
    responses: dict[str, int], bank: list[dict]
) -> dict[str, Any]:
    """Full-inventory result dict, same shape as the adaptive scorer."""
    riasec = scoring.interest_scores(responses, bank)
    return {
        "riasec": riasec,
        "top3_code": scoring.top3_code(riasec),
        "items_answered": len(responses),
    }


def reference_top3(
    persona_latent: dict[str, float], bank: list[dict], seed: int, noise: float = 0.15
) -> str:
    """The Holland code a respondent *would* get on the full bank."""
    responses = respondent_responses(persona_latent, bank, seed, noise=noise)
    return full_scores(responses, bank)["top3_code"]


def respondent_responses(
    persona_latent: dict[str, float], bank: list[dict], seed: int, noise: float = 0.15
) -> dict[str, int]:
    """One respondent's answer to *every* item, drawn once from a seeded RNG.

    Generating the whole vector up front lets the adaptive run and the full
    reference read the *same* responses — the standard short-form validity
    protocol (everyone answers the full inventory; we check the adaptive subset
    reproduces the full-score ranking). Independent draws would confound G4 with
    sampling noise.
    """
    rng = random.Random(f"resp:{seed}:{sorted(persona_latent.items())}")
    return full_bank_responses(persona_latent, bank, rng, noise=noise)


def adaptive_top3(
    responses: dict[str, int], bank: list[dict]
) -> tuple[str, int]:
    """Drive the adaptive interest engine over a *fixed* response vector.

    The engine chooses which item to ask; the respondent's answer to that item
    is looked up in `responses` (the same vector the full reference is scored
    from). Returns (top3_code, n_interest_items).
    """
    state = adaptive.new_state()
    while True:
        item = adaptive.next_interest_item(state, bank)
        if item is None or adaptive.is_interest_complete(state, bank):
            break
        adaptive.record_interest_answer(state, bank, item["id"], responses[item["id"]])
    return state["top3_code"], len(state["interest_responses"])

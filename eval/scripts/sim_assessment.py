#!/usr/bin/env python3
"""G4 evaluation for the adaptive assessment engine (PHASE_2.md).

Replays a *synthetic* RIASEC respondent dataset through both the adaptive
engine (<=24 items) and the full-inventory reference, then reports:

  * G4      = % of respondents whose adaptive top-3 **letter set** matches the
              full-test reference set (target >= 95%)
  * order%  = % whose full ordered 3-letter code matches (reported for honesty;
              the fine order of three near-tied dimensions is genuinely fragile
              in short form)
  * avg interest items asked (target <= 24)

DATASET + LICENCE
-----------------
This is a **SYNTHETIC** dataset generated in-process — there is no external
survey file and we do NOT claim real-world G4 (PS 26241 ships only dummy data at
evaluation, and PHASE_2.md requires the synthetic label). Licence: none / N/A.

Generation model, per dimension latent in [0,1]:
  - 80% "clear-cut" respondents: 3 dominant dimensions in U[0.80, 0.98] and the
    other 3 in U[0.02, 0.28] (a well-separated Holland profile);
  - 20% "ambiguous" respondents: all 6 in U[0.15, 0.85] (weakly ordered, harder).
Each respondent answers the whole bank **once** from a single seeded Gaussian
(sigma = NOISE) response vector; the adaptive subset and the full reference are
scored from that *same* vector, so G4 measures item-selection fidelity, not
response randomness.

Run:  python eval/scripts/sim_assessment.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND))

from app.ml.assessment import adaptive, scoring_full  # noqa: E402

DIMENSIONS = ("R", "I", "A", "S", "E", "C")
N_CLEAR = 160
N_AMBIG = 40
NOISE = 0.10
SEED = 2026


def make_personas(seed: int) -> list[dict[str, float]]:
    """A mix of clear-cut and ambiguous synthetic Holland profiles."""
    rng = random.Random(seed)
    personas: list[dict[str, float]] = []
    for _ in range(N_CLEAR):
        top = set(rng.sample(DIMENSIONS, 3))
        high = iter(sorted(rng.uniform(0.80, 0.98) for _ in range(3)))
        low = iter(sorted(rng.uniform(0.02, 0.28) for _ in range(3)))
        personas.append({d: (next(high) if d in top else next(low)) for d in DIMENSIONS})
    for _ in range(N_AMBIG):
        personas.append({d: rng.uniform(0.15, 0.85) for d in DIMENSIONS})
    return personas


def main() -> int:
    bank = adaptive.load_interest_bank()
    personas = make_personas(SEED)

    set_matches = 0
    order_matches = 0
    item_counts: list[int] = []
    for i, latent in enumerate(personas):
        responses = scoring_full.respondent_responses(latent, bank, seed=i, noise=NOISE)
        reference = scoring_full.full_scores(responses, bank)["top3_code"]
        adaptive_code, n_items = scoring_full.adaptive_top3(responses, bank)
        item_counts.append(n_items)
        set_matches += set(adaptive_code) == set(reference)
        order_matches += adaptive_code == reference

    total = len(personas)
    g4 = set_matches / total * 100.0
    order_pct = order_matches / total * 100.0
    avg_items = sum(item_counts) / total
    early = sum(1 for n in item_counts if n < adaptive.TARGET_ITEMS) / total * 100.0

    print("=== Assessment engine — G4 simulation (SYNTHETIC dataset) ===")
    print(f"respondents replayed : {total} (synthetic, seed={SEED}, noise=sd{NOISE})")
    print(f"G4 top-3 agreement   : {g4:.1f}%   target >= 95%")
    print(f"exact-order agreement: {order_pct:.1f}%   (informational)")
    print(f"avg interest items   : {avg_items:.1f}   target <= 24")
    print(f"max interest items   : {max(item_counts)}   hard cap {adaptive.HARD_CAP}")
    print(f"stopped before 24    : {early:.0f}% of respondents")
    print(
        "NOTE: SYNTHETIC respondents — NOT a claim of real-world G4 "
        "(PS 26241 provides dummy data only at evaluation)."
    )

    ok = g4 >= 95.0 and avg_items <= adaptive.TARGET_ITEMS
    print(f"RESULT: {'PASS' if ok else 'BELOW TARGET'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

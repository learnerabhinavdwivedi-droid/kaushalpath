"""Scoring primitives for the assessment engine (no selection logic here).

Turns raw item responses into normalised scores:
- interest (RIASEC)  -> each dimension in [0, 1], from a 1..5 Likert answer
- aptitude           -> each dimension in [0, 1], the fraction answered correctly

`adaptive.py` uses these functions to recompute a session snapshot after every
answer; `scoring_full.py` uses them over the *entire* item bank as the reference
test for the G4 evaluation metric.
"""
from __future__ import annotations

import math
from collections import defaultdict

RIASEC_DIMS = ("R", "I", "A", "S", "E", "C")
APTITUDE_DIMS = ("num", "verbal", "spatial", "mech")


def signed(value: int, reverse: bool = False) -> float:
    """Map a 1..5 Likert answer to [-1, 1]; flip sign for reverse-scored items."""
    x = (value - 3) / 2.0
    if reverse:
        x = -x
    return max(-1.0, min(1.0, x))


def interest_scores(responses: dict[str, int], bank: list[dict]) -> dict[str, float]:
    """Normalised [0,1] score per RIASEC dimension (mean of signed answers).

    Dimensions with no answers yet default to the neutral midpoint 0.5 so the
    top-3 code is always well-defined.
    """
    xs: dict[str, list[float]] = defaultdict(list)
    for item in bank:
        value = responses.get(item["id"])
        if value is None:
            continue
        xs[item["dimension"]].append(signed(value, item.get("reverse", False)))
    out: dict[str, float] = {}
    for dim in RIASEC_DIMS:
        vals = xs.get(dim, [])
        out[dim] = (sum(vals) / len(vals) + 1) / 2 if vals else 0.5
    return out


def top3_code(scores: dict[str, float]) -> str:
    """Holland code: top-3 dimensions by score, ordered (ties broken alphabetically)."""
    ordered = sorted(RIASEC_DIMS, key=lambda d: (-scores.get(d, 0.0), d))
    return "".join(ordered[:3])


def aptitude_scores(responses: dict[str, bool], bank: list[dict]) -> dict[str, float]:
    """Fraction correct per aptitude dimension in [0,1]; 0.0 if none answered yet."""
    total: dict[str, int] = defaultdict(int)
    correct: dict[str, int] = defaultdict(int)
    for item in bank:
        if item["id"] in responses:
            dim = item["dimension"]
            total[dim] += 1
            correct[dim] += 1 if responses[item["id"]] else 0
    out: dict[str, float] = {}
    for dim in APTITUDE_DIMS:
        out[dim] = correct[dim] / total[dim] if total[dim] else 0.0
    return out


def probability_scores(theta_dict: dict[str, float]) -> dict[str, float]:
    """Map RIASEC latent ability thetas to probabilities via standard sigmoid."""
    return {d: 1.0 / (1.0 + math.exp(-theta_dict.get(d, 0.0))) for d in RIASEC_DIMS}


"""Scoring primitives for the assessment engine (Phase 21).

Turns raw item responses into normalised scores:
- interest (RIASEC)  -> each dimension in [0, 1], from 1..5 Likert, 1..3 Likert, or paired ties.
- aptitude           -> each dimension in [0, 1], the fraction answered correctly.

`adaptive.py` uses these functions to recompute a session snapshot after every answer.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any

RIASEC_DIMS = ("R", "I", "A", "S", "E", "C")
APTITUDE_DIMS = ("num", "verbal", "spatial", "mech")


def signed(value: int | float, reverse: bool = False, scale: int = 5) -> float:
    """Map a Likert answer to [-1, 1]; flip sign for reverse-scored items.

    Supports:
    - 1..5 scale (default): 1 -> -1.0, 2 -> -0.5, 3 -> 0.0, 4 -> 0.5, 5 -> 1.0
    - 1..3 scale (likert3): 1 -> -1.0 (dislike), 2 -> 0.0 (unsure), 3 -> 1.0 (like)
    """
    v = float(value)
    if scale == 3 or (1.0 <= v <= 3.0 and v == int(v) and v in (1, 2, 3) and scale != 5):
        x = v - 2.0  # 1 -> -1, 2 -> 0, 3 -> 1
    else:
        x = (v - 3.0) / 2.0
    if reverse:
        x = -x
    return max(-1.0, min(1.0, x))


def interest_scores(
    responses: dict[str, Any],
    bank: list[dict],
    pair_adjustments: dict[str, float] | None = None,
) -> dict[str, float]:
    """Normalised [0,1] score per RIASEC dimension (mean of signed answers + pair ties).

    Dimensions with no answers yet default to the neutral midpoint 0.5 so the
    top-3 code is always well-defined.
    """
    xs: dict[str, list[float]] = defaultdict(list)
    for item in bank:
        value = responses.get(item["id"])
        if value is None or not isinstance(value, (int, float)):
            continue
        xs[item["dimension"]].append(signed(value, item.get("reverse", False)))

    out: dict[str, float] = {}
    adjustments = pair_adjustments or {}
    for dim in RIASEC_DIMS:
        vals = xs.get(dim, [])
        base = sum(vals) / len(vals) if vals else 0.0
        # Add tie-break adjustment if any (each adjustment is on signed [-1, 1] scale)
        adj = adjustments.get(dim, 0.0)
        adj_scaled = base + adj
        out[dim] = max(0.0, min(1.0, (adj_scaled + 1.0) / 2.0))
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
            dim = item.get("construct") or item.get("dimension")
            if dim in APTITUDE_DIMS:
                total[dim] += 1
                correct[dim] += 1 if responses[item["id"]] else 0
    out: dict[str, float] = {}
    for dim in APTITUDE_DIMS:
        out[dim] = correct[dim] / total[dim] if total[dim] else 0.0
    return out


def probability_scores(theta_dict: dict[str, float]) -> dict[str, float]:
    """Map RIASEC latent ability thetas to probabilities via standard sigmoid."""
    return {d: 1.0 / (1.0 + math.exp(-theta_dict.get(d, 0.0))) for d in RIASEC_DIMS}

"""Pure Aptitude Fit matching module (Phase 21 Item F).

Matches learner assessed abilities against occupation ability requirements:
    aptitude_match(learner_theta, learner_se, occ_requirements) -> {score, shortfalls, confidence}

Principles:
1. Percentile linking:
   - Learner percentiles linked against normative pilot distribution.
   - Occupation requirements linked against distribution across vocational occupations.
2. Shortfall only:
   - If learner ability is below occupation requirement, count gap as shortfall.
   - If learner ability exceeds requirement (surplus), shortfall is 0.0 (surplus not penalized).
3. Empirical Bayes / SEM Shrinkage:
   - When measurement error (SE) is high, shrink score toward midpoint (0.50).
"""
from __future__ import annotations

import math
from typing import Any

CONSTRUCTS = ("num", "verbal", "spatial", "mech")

# Default normative parameters (mean, sd) for learner percentiles and occupation distributions
DEFAULT_LEARNER_NORMS: dict[str, tuple[float, float]] = {
    "num": (0.50, 0.20),
    "verbal": (0.50, 0.20),
    "spatial": (0.50, 0.20),
    "mech": (0.50, 0.20),
}

DEFAULT_OCC_NORMS: dict[str, tuple[float, float]] = {
    "num": (0.45, 0.22),
    "verbal": (0.40, 0.22),
    "spatial": (0.42, 0.22),
    "mech": (0.48, 0.22),
}


def _norm_cdf(x: float, mean: float = 0.5, sd: float = 0.2) -> float:
    """Standard normal cumulative distribution function mapped to [0, 1]."""
    if sd <= 1e-6:
        return 0.5
    z = (x - mean) / (sd * math.sqrt(2.0))
    return max(0.001, min(0.999, 0.5 * (1.0 + math.erf(z))))


def aptitude_match(
    learner_theta: dict[str, float],
    learner_se: dict[str, float] | None,
    occ_requirements: dict[str, float],
    learner_norms: dict[str, tuple[float, float]] | None = None,
    occ_norms: dict[str, tuple[float, float]] | None = None,
) -> dict[str, Any]:
    """Calculate aptitude match score, construct-level shortfalls, and measurement confidence.

    Args:
        learner_theta: dict of learner ability scores per construct in [0, 1].
        learner_se: dict of learner measurement standard errors per construct.
        occ_requirements: dict of occupation required abilities per construct in [0, 1].
        learner_norms: optional (mean, sd) norms for learner abilities.
        occ_norms: optional (mean, sd) norms for occupation requirements.

    Returns:
        dict with:
            "score": float in [0, 1], shrunk toward 0.5 when confidence is low.
            "shortfalls": dict mapping construct to shortfall gap in [0, 1] (0 if learner >= req).
            "confidence": float in [0, 1] based on standard error.
    """
    l_norms = learner_norms or DEFAULT_LEARNER_NORMS
    o_norms = occ_norms or DEFAULT_OCC_NORMS
    se_map = learner_se or {}

    shortfalls: dict[str, float] = {}
    se_values: list[float] = []

    for c in CONSTRUCTS:
        theta_c = float(learner_theta.get(c, 0.5))
        req_c = float(occ_requirements.get(c, 0.0))
        se_c = float(se_map.get(c, 0.15))
        se_values.append(max(0.01, se_c))

        # Convert to percentile ranks
        l_mean, l_sd = l_norms.get(c, (0.5, 0.2))
        o_mean, o_sd = o_norms.get(c, (0.5, 0.2))

        learner_p = _norm_cdf(theta_c, l_mean, l_sd)
        req_p = _norm_cdf(req_c, o_mean, o_sd)

        # SHORTFALL only: if learner is below requirement, record shortfall; surplus not penalized
        if learner_p < req_p:
            gap = req_p - learner_p
        else:
            gap = 0.0
        shortfalls[c] = round(gap, 4)

    # Base match score: 1.0 minus average shortfall across constructs
    avg_shortfall = sum(shortfalls.values()) / len(CONSTRUCTS)
    raw_score = max(0.0, min(1.0, 1.0 - avg_shortfall))

    # Confidence calculation: lower standard error -> higher confidence
    mean_se = sum(se_values) / len(se_values)
    # se in [0.05, 0.35] maps confidence to [0.90, 0.30]
    confidence = max(0.20, min(1.0, 1.0 - (mean_se / 0.5)))

    # Shrinkage: when SE is high (low confidence), shrink score toward neutral 0.50
    shrunk_score = confidence * raw_score + (1.0 - confidence) * 0.50

    return {
        "score": round(shrunk_score, 4),
        "shortfalls": shortfalls,
        "confidence": round(confidence, 4),
    }

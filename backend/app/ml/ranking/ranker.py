"""Phase 3: Ranker for Recommendations.

Tries to load a trained LightGBM LambdaRank booster from disk; if the file or
the optional `lightgbm` native lib is missing, falls back to a transparent,
config-weighted scorer (per the spec). `lightgbm`/`numpy` are imported lazily so
merely importing this module — and therefore `app.main` — never loads the heavy
native stack.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import get_settings
from app.ml.paths import RANKER_MODEL_PATH
from app.ml.ranking.features import to_vector as _to_vector

logger = logging.getLogger(__name__)


class Ranker:
    def __init__(self, use_model: bool = True):
        self.model = None
        self.settings = get_settings()
        if use_model:
            self._load_model()

    def _load_model(self) -> None:
        # LightGBM's C library can clash with FAISS/torch on Windows, so only
        # import it when a trained model file actually exists.
        if not RANKER_MODEL_PATH.exists():
            logger.info(
                "No trained ranker at %s; using fallback weighted scorer.", RANKER_MODEL_PATH
            )
            return
        try:
            import lightgbm as lgb

            self.model = lgb.Booster(model_file=str(RANKER_MODEL_PATH))
            logger.info("LightGBM ranker loaded from %s.", RANKER_MODEL_PATH)
        except Exception as exc:
            logger.warning("Could not load LightGBM model (%s); using fallback scorer.", exc)
            self.model = None

    def _fallback_score(
        self,
        features: dict[str, Any],
        *,
        interest_confidence: float = 1.0,
    ) -> float:
        s = self.settings

        # Normalise higher-is-better representations
        raw_dist = features.get("distance_km")
        dist_score = (1.0 - min(raw_dist / 500.0, 1.0)) if raw_dist is not None else None

        raw_cost = features.get("net_cost_ratio")
        if raw_cost is None:
            raw_cost = features.get("fee_ratio")
        cost_score = (1.0 - min(raw_cost, 1.0)) if raw_cost is not None else None

        raw_prog = features.get("progression_value")
        prog_score = min(raw_prog / 3.0, 1.0) if raw_prog is not None else None

        feature_values: dict[str, float | None] = {
            "riasec_cosine": features.get("riasec_cosine"),
            "top3_code_overlap": features.get("top3_code_overlap"),
            "aptitude_fit_occ": features.get("aptitude_fit_occ", features.get("aptitude_fit")),
            "placement_est": features.get("placement_est"),
            "earnings_median_pct": features.get("earnings_median_pct"),
            "earnings_floor_pct": features.get("earnings_floor_pct"),
            "local_demand": features.get("local_demand", features.get("local_demand_index")),
            "net_cost_score": cost_score,
            "distance_score": dist_score,
            "progression_value": prog_score,
        }

        # Base transparent weights per Phase 23 Step 4 (sum = 1.0)
        base_weights: dict[str, float] = {
            "riasec_cosine": getattr(s, "ranker_weight_riasec", 0.22),
            "top3_code_overlap": getattr(s, "ranker_weight_overlap", 0.08),
            "aptitude_fit_occ": getattr(s, "ranker_weight_aptitude", 0.20),
            "placement_est": getattr(s, "ranker_weight_placement", 0.10),
            "earnings_median_pct": getattr(s, "ranker_weight_earnings_median", 0.08),
            "earnings_floor_pct": getattr(s, "ranker_weight_earnings_floor", 0.07),
            "local_demand": getattr(s, "ranker_weight_local_demand", 0.08),
            "net_cost_score": getattr(s, "ranker_weight_net_cost", 0.07),
            "distance_score": getattr(s, "ranker_weight_distance", 0.05),
            "progression_value": getattr(s, "ranker_weight_progression", 0.05),
        }

        # Shift weight from interest to aptitude & outcomes when interest_confidence is low
        weights = dict(base_weights)
        c = max(0.0, min(1.0, float(interest_confidence)))
        if c < 0.70:
            shift_ratio = (0.70 - c) / 0.70
            tot_interest = weights["riasec_cosine"] + weights["top3_code_overlap"]
            shift_amt = tot_interest * shift_ratio * 0.5
            w_riasec = weights["riasec_cosine"]
            w_top3 = weights["top3_code_overlap"]
            weights["riasec_cosine"] -= shift_amt * (w_riasec / tot_interest)
            weights["top3_code_overlap"] -= shift_amt * (w_top3 / tot_interest)
            weights["aptitude_fit_occ"] += shift_amt * 0.40
            outcomes_tot = (
                weights["placement_est"]
                + weights["earnings_median_pct"]
                + weights["earnings_floor_pct"]
            )
            if outcomes_tot > 0:
                share_pl = weights["placement_est"] / outcomes_tot
                share_med = weights["earnings_median_pct"] / outcomes_tot
                share_fl = weights["earnings_floor_pct"] / outcomes_tot
                weights["placement_est"] += shift_amt * 0.60 * share_pl
                weights["earnings_median_pct"] += shift_amt * 0.60 * share_med
                weights["earnings_floor_pct"] += shift_amt * 0.60 * share_fl

        # Missing data neutrality (Step 3):
        # Renormalise weights across available features only; never fill 0.5 constants
        present_weights = 0.0
        weighted_sum = 0.0
        for name, val in feature_values.items():
            if val is not None:
                w = weights.get(name, 0.0)
                present_weights += w
                weighted_sum += w * float(val)

        if present_weights > 0:
            return round(weighted_sum / present_weights, 4)
        return 0.5

    def score(self, features: dict, *, interest_confidence: float = 1.0) -> float:
        if self.model is not None:
            try:
                import numpy as np

                vec = np.array([_to_vector(features)], dtype="float32")
                return float(self.model.predict(vec)[0])
            except Exception as exc:
                logger.warning("Model predict failed (%s); using fallback.", exc)
        return self._fallback_score(features, interest_confidence=interest_confidence)

    def rank(self, items: list[dict], *, interest_confidence: float = 1.0) -> list[dict]:
        """Sort items (each carrying a 'features' dict) by score, descending."""
        for item in items:
            item["score"] = self.score(item["features"], interest_confidence=interest_confidence)
        return sorted(items, key=lambda x: x["score"], reverse=True)

    @property
    def model_version(self) -> str:
        return self.settings.model_version

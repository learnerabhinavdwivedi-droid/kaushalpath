"""Phase 3: Ranker for Recommendations.

Tries to load a trained LightGBM LambdaRank booster from disk; if the file or
the optional `lightgbm` native lib is missing, falls back to a transparent,
config-weighted scorer (per the spec). `lightgbm`/`numpy` are imported lazily so
merely importing this module — and therefore `app.main` — never loads the heavy
native stack.
"""
from __future__ import annotations

import logging

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

    def _fallback_score(self, features: dict) -> float:
        s = self.settings
        g = features.get
        # Higher-is-better signals
        score = (
            g("riasec_cosine", 0.0) * s.ranker_weight_riasec
            + g("top3_code_overlap", 0.0) * s.ranker_weight_overlap
            + g("aptitude_fit", 0.0) * s.ranker_weight_aptitude
            + g("local_demand_index", 0.0) * s.ranker_weight_demand
            + g("salary_percentile", 0.0) * s.ranker_weight_salary
            + g("retrieval_score", 0.0) * s.ranker_weight_retrieval
        )
        # Lower-is-better signals (subtract their cost, scaled to ~[0,1])
        score -= g("fee_ratio", 0.0) * s.ranker_weight_fee
        score -= g("nsqf_gap", 0.0) * s.ranker_weight_nsqf
        score -= min(g("distance_km", 0.0) / 500.0, 1.0) * s.ranker_weight_distance
        return score

    def score(self, features: dict) -> float:
        if self.model is not None:
            try:
                import numpy as np

                vec = np.array([_to_vector(features)], dtype="float32")
                return float(self.model.predict(vec)[0])
            except Exception as exc:
                logger.warning("Model predict failed (%s); using fallback.", exc)
        return self._fallback_score(features)

    def rank(self, items: list[dict]) -> list[dict]:
        """Sort items (each carrying a 'features' dict) by score, descending."""
        for item in items:
            item["score"] = self.score(item["features"])
        return sorted(items, key=lambda x: x["score"], reverse=True)

    @property
    def model_version(self) -> str:
        return self.settings.model_version

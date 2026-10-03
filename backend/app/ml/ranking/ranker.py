"""Phase 3: Ranker for Recommendations."""
import logging
import os
from typing import Any

import lightgbm as lgb
import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)

MODEL_PATH = "data/processed/ranker_model.txt"

class Ranker:
    def __init__(self):
        self.model = None
        self.settings = get_settings()
        self._load_model()

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                self.model = lgb.Booster(model_file=MODEL_PATH)
                logger.info("LightGBM model loaded.")
            except Exception as e:
                logger.error(f"Failed to load LightGBM model: {e}")
        else:
            logger.warning("LightGBM model not found. Using fallback transparent weighted scorer.")

    def score(self, features: dict[str, float]) -> float:
        if self.model is not None:
            # We would need to pass features in the exact same order as training
            feature_vector = np.array([[
                features.get("riasec_cosine", 0.0),
                features.get("top3_code_overlap", 0.0),
                features.get("aptitude_fit", 0.0),
                features.get("nsqf_gap", 0.0),
                features.get("fee_ratio", 0.0),
                features.get("duration_fit", 0.0),
                features.get("retrieval_score", 0.0)
            ]])
            return float(self.model.predict(feature_vector)[0])
        else:
            # Fallback transparent weighted scorer
            score = (
                features.get("riasec_cosine", 0.0) * self.settings.ranker_weight_riasec +
                features.get("aptitude_fit", 0.0) * self.settings.ranker_weight_aptitude +
                features.get("fee_ratio", 0.0) * self.settings.ranker_weight_fee +
                features.get("retrieval_score", 0.0) * self.settings.ranker_weight_retrieval
            )
            return score

    def rank(self, items: list[dict]) -> list[dict]:
        """Rank a list of items based on their extracted features.
        
        items should be a list of dicts like:
        {"course": Course, "occupation": Occupation, "features": dict}
        
        Returns the items sorted by score descending, with a "score" key added.
        """
        for item in items:
            item["score"] = self.score(item["features"])
        
        return sorted(items, key=lambda x: x["score"], reverse=True)

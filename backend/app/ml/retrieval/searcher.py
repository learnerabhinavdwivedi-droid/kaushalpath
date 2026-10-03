"""Phase 3: Searcher for retrieving top occupations."""
import json
import logging
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from app.ml.retrieval.embedder import get_embedder

logger = logging.getLogger(__name__)

INDEX_PATH = Path("data/processed/occupation_index.faiss")
MAPPING_PATH = Path("data/processed/occupation_mapping.json")

class Searcher:
    def __init__(self):
        self.embedder = get_embedder()
        self.index = None
        self.mapping = {}
        self._load_index()

    def _load_index(self):
        if not INDEX_PATH.exists() or not MAPPING_PATH.exists():
            logger.warning("FAISS index or mapping not found. Please build the index first.")
            return

        self.index = faiss.read_index(str(INDEX_PATH))
        with open(MAPPING_PATH, "r") as f:
            mapping_str = json.load(f)
            self.mapping = {int(k): v for k, v in mapping_str.items()}

    def search(self, top_riasec: list[str], aptitudes: list[str], stated_interests: str, top_k: int = 10) -> list[tuple[int, float]]:
        """Search for occupations matching the profile.
        
        Returns:
            list of tuples: (occupation_id, score)
        """
        if not self.index:
            logger.error("Index is not loaded.")
            return []

        # Construct query text
        query_parts = []
        if top_riasec:
            query_parts.append(f"Strong interests in {', '.join(top_riasec)}.")
        if aptitudes:
            query_parts.append(f"Strong aptitudes in {', '.join(aptitudes)}.")
        if stated_interests:
            query_parts.append(f"Specifically interested in: {stated_interests}.")
            
        query_text = " ".join(query_parts)
        
        if not query_text:
            return []

        query_emb = self.embedder.encode(query_text, normalize_embeddings=True)
        query_emb_np = np.array([query_emb]).astype("float32")

        # Search FAISS
        distances, indices = self.index.search(query_emb_np, top_k)
        
        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx in self.mapping:
                occ_id = self.mapping[idx]
                score = distances[0][i]
                results.append((occ_id, float(score)))

        return results

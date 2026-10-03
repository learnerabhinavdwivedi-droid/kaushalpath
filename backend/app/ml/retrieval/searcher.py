"""Phase 3: Searcher for retrieving top occupations.

FAISS and the embedding model are imported lazily so the API boots in a minimal
environment. When the index file is absent or the native stack is unavailable,
`search()` returns an empty list and the pipeline still ranks on the remaining
features (graceful degradation rather than a crash).
"""
import json
import logging
from pathlib import Path

from app.ml.paths import OCCUPATION_INDEX_PATH, OCCUPATION_MAPPING_PATH
from app.ml.retrieval.embedder import get_embedder

logger = logging.getLogger(__name__)


class Searcher:
    def __init__(self):
        self.embedder = get_embedder()
        self.index = None
        self.mapping: dict[int, object] = {}
        self._loaded = False

    def _load_index(self) -> bool:
        if self._loaded:
            return self.index is not None
        self._loaded = True
        if not Path(OCCUPATION_INDEX_PATH).exists() or not Path(OCCUPATION_MAPPING_PATH).exists():
            logger.info("FAISS index/mapping not found; retrieval disabled until `make seed`.")
            return False
        try:
            import faiss
        except Exception as exc:  # native lib unavailable
            logger.warning("faiss not importable (%s); retrieval disabled.", exc)
            return False
        try:
            self.index = faiss.read_index(str(OCCUPATION_INDEX_PATH))
            with open(OCCUPATION_MAPPING_PATH, encoding="utf-8") as f:
                self.mapping = {int(k): v for k, v in json.load(f).items()}
        except Exception as exc:
            logger.warning("Could not load FAISS index (%s); retrieval disabled.", exc)
            self.index = None
            return False
        return True

    def available(self) -> bool:
        return self._load_index() and self.embedder.available()

    def search(
        self,
        top_riasec: list[str],
        aptitudes: list[str],
        stated_interests: str,
        top_k: int = 10,
    ) -> list[tuple[int, float]]:
        """Return [(occupation_id, cosine_score)] for the profile query.

        An empty list means retrieval is unavailable — callers must not treat a
        zero retrieval score as a penalty.
        """
        if not self._load_index():
            return []

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

        try:
            import numpy as np

            query_emb = self.embedder.encode(query_text, normalize_embeddings=True)
            query_emb_np = np.array([query_emb]).astype("float32")
            distances, indices = self.index.search(query_emb_np, top_k)
        except Exception as exc:
            logger.warning("Retrieval query failed (%s); returning no matches.", exc)
            return []

        results = []
        for i in range(len(indices[0])):
            idx = indices[0][i]
            if idx in self.mapping:
                results.append((self.mapping[idx], float(distances[0][i])))
        return results

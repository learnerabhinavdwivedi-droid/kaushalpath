"""Phase 3: Text embedding wrapper for retrieval.

`sentence_transformers` pulls in `torch`, whose native DLLs are heavy (and can
clash with FAISS on Windows). Importing it lazily keeps `app.main` importable in
a minimal environment — embeddings are only constructed when a caller actually
asks for a vector (i.e. when building the index or running a live query).
"""
import os
from functools import lru_cache
from typing import Any

from app.core.config import get_settings


class EmbedderUnavailable(RuntimeError):
    """Raised when the optional sentence-transformers/torch stack is missing."""


class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        # Cache dir so dev runs don't re-download repeatedly.
        cache_root = os.path.dirname(__file__)
        cache_dir = os.path.join(cache_root, "..", "..", ".cache", "sentence_transformers")
        os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", cache_dir)
        self._model: Any | None = None

    def _lazy_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except Exception as exc:  # ImportError or native DLL load failure
                raise EmbedderUnavailable(
                    f"sentence-transformers/torch unavailable ({exc}); "
                    "retrieval is disabled."
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def available(self) -> bool:
        try:
            self._lazy_model()
            return True
        except EmbedderUnavailable:
            return False

    def encode(self, texts: list[str] | str, normalize_embeddings: bool = True) -> Any:
        return self._lazy_model().encode(texts, normalize_embeddings=normalize_embeddings)


@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return Embedder(settings.embedder_model_name)

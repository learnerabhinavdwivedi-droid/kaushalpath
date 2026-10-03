"""Phase 3: Text embedding wrapper for retrieval."""
import os
from functools import lru_cache
from typing import Any

from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

class Embedder:
    def __init__(self, model_name: str):
        self.model_name = model_name
        # Set cache dir to avoid downloading repeatedly in dev
        os.environ["SENTENCE_TRANSFORMERS_HOME"] = "./.cache/sentence_transformers"
        self.model = SentenceTransformer(self.model_name)

    def encode(self, texts: list[str] | str, normalize_embeddings: bool = True) -> Any:
        return self.model.encode(texts, normalize_embeddings=normalize_embeddings)

@lru_cache
def get_embedder() -> Embedder:
    settings = get_settings()
    return Embedder(settings.embedder_model_name)

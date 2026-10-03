"""Phase 3: FAISS Index builder for occupations.

Text indexed = name + description + skills (the spec's field set). Writes go to
the absolute `app/ml/paths.PROCESSED_DIR`, so the seed process and the API agree
regardless of the working directory. `faiss`/numpy are imported lazily.
"""
import json
import logging
from pathlib import Path

from app.ml.paths import OCCUPATION_INDEX_PATH, OCCUPATION_MAPPING_PATH
from app.ml.retrieval.embedder import EmbedderUnavailable, get_embedder

logger = logging.getLogger(__name__)


def _occupation_text(occ) -> str:
    parts = [occ.name_en or ""]
    if getattr(occ, "description", None):
        parts.append(occ.description)
    skills = getattr(occ, "skills", None)
    if skills:
        parts.append(skills if isinstance(skills, str) else " ".join(map(str, skills)))
    return ". ".join(p for p in parts if p).strip()


def build_index(occupations: list) -> bool:
    """Build + persist a FAISS index over occupation text.

    Returns True on success. Returns False (and logs why) when the optional
    native stack is unavailable so the seed step degrades instead of crashing.
    """
    if not occupations:
        logger.warning("No occupations provided for index building.")
        return False

    embedder = get_embedder()
    occ_texts = [_occupation_text(o) for o in occupations]
    try:
        embeddings = embedder.encode(occ_texts, normalize_embeddings=True)
    except EmbedderUnavailable as exc:
        logger.warning("Embedder unavailable; skipping index build: %s", exc)
        return False

    try:
        import faiss
        import numpy as np
    except Exception as exc:  # native lib unavailable
        logger.warning("faiss not importable; skipping index build: %s", exc)
        return False

    embeddings_np = np.array(embeddings).astype("float32")
    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dimension)  # inner product == cosine for normalised vectors
    index.add(embeddings_np)

    Path(OCCUPATION_INDEX_PATH).parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(OCCUPATION_INDEX_PATH))

    mapping = {i: occ.id for i, occ in enumerate(occupations)}
    with open(OCCUPATION_MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f)

    logger.info(
        "Wrote FAISS index for %d occupations to %s", len(occupations), OCCUPATION_INDEX_PATH
    )
    return True

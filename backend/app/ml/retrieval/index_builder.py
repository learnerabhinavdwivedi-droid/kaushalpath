"""Phase 3: FAISS Index builder for occupations."""
import json
import logging
from pathlib import Path

import faiss
import numpy as np

from app.ml.retrieval.embedder import get_embedder

logger = logging.getLogger(__name__)

INDEX_PATH = Path("data/processed/occupation_index.faiss")
MAPPING_PATH = Path("data/processed/occupation_mapping.json")

def build_index(occupations: list) -> None:
    """Builds a FAISS index over occupation text and saves to disk."""
    if not occupations:
        logger.warning("No occupations provided for index building.")
        return

    embedder = get_embedder()
    
    texts = []
    mapping = {}
    for i, occ in enumerate(occupations):
        # Combine name and description for semantic search
        name = occ.name_en or ""
        desc = occ.description or ""
        text = f"{name}. {desc}".strip()
        texts.append(text)
        mapping[i] = occ.id

    logger.info(f"Encoding {len(texts)} occupations...")
    embeddings = embedder.encode(texts, normalize_embeddings=True)
    embeddings_np = np.array(embeddings).astype("float32")

    dimension = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dimension)  # Inner product since embeddings are normalized (Cosine similarity)
    
    logger.info("Adding vectors to FAISS index...")
    index.add(embeddings_np)

    # Ensure dir exists
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)

    logger.info(f"Writing index to {INDEX_PATH}")
    faiss.write_index(index, str(INDEX_PATH))

    with open(MAPPING_PATH, "w") as f:
        json.dump(mapping, f)
        
    logger.info("Index building complete.")

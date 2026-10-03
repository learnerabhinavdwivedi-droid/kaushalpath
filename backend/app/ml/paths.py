"""Absolute locations for ML artefacts (FAISS index, ranker model).

Resolving from `__file__` (not the process CWD) keeps the seed step that
*writes* the index and the API that *reads* it in agreement regardless of the
launch directory (`uvicorn --app-dir backend` runs with CWD=backend, while
`python scripts/seed_all.py` runs from the repo root). The directory is created
on import so writes never fail on a missing parent.
"""
from __future__ import annotations

from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]  # .../kaushalpath/backend
PROCESSED_DIR = BACKEND_DIR / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

OCCUPATION_INDEX_PATH = PROCESSED_DIR / "occupation_index.faiss"
OCCUPATION_MAPPING_PATH = PROCESSED_DIR / "occupation_mapping.json"
RANKER_MODEL_PATH = PROCESSED_DIR / "ranker_model.txt"
RANKER_META_PATH = PROCESSED_DIR / "ranker_meta.json"

# Gold eval artefacts live at the repo root (shared with the eval scripts).
REPO_ROOT = BACKEND_DIR.parent
GOLD_DIR = REPO_ROOT / "eval" / "gold"
PERSONAS_PATH = GOLD_DIR / "personas.jsonl"
GOLD_LABELS_PATH = GOLD_DIR / "labels.jsonl"

"""Phase 3: Build the FAISS occupation retrieval index from the seeded DB.

Invoked at the end of `make seed`. Degrades to a no-op (with a log) when the
optional embedding/FAISS stack is unavailable, so seeding never hard-fails.

Run: python scripts/build_retrieval_index.py
"""
from __future__ import annotations

import _common  # noqa: F401  # bootstraps sys.path so app.* resolves
from app.db import SessionLocal
from app.ml.retrieval.index_builder import build_index
from app.services import data_repo


def main() -> None:
    with SessionLocal() as session:
        occupations = list(data_repo.get_occupations(session))
    if not occupations:
        print("build_retrieval_index: no occupations seeded; nothing to do.")
        return
    built = build_index(occupations)
    if built:
        print(f"build_retrieval_index: indexed {len(occupations)} occupations.")
    else:
        print("build_retrieval_index: skipped (embedding/FAISS stack unavailable).")


if __name__ == "__main__":
    main()

"""CLI: export the feedback table into the retraining dataset.

Usage (from the backend dir, or anywhere — paths are __file__-anchored):
    python -m scripts.export_feedback        # or: python scripts/export_feedback.py

Writes ``backend/data/processed/retrain_feedback.jsonl``. NEVER touches
``eval/gold`` (the accuracy contract requires an untouched gold set).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Allow running both as a module and as a plain script from the backend dir.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.feedback_export_svc import export_feedback  # noqa: E402


def main() -> None:
    with SessionLocal() as db:
        summary = export_feedback(db)
    print(
        f"exported {summary['n_samples']} feedback sample(s) "
        f"({summary['n_positive']} positive) -> {summary['path']}"
    )


if __name__ == "__main__":
    main()

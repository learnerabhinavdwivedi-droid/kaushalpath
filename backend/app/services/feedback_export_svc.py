"""Phase 8: feedback -> retraining-dataset export.

Merges the ``feedback`` table onto the stored recommendations it rates and
writes ONE retraining artefact (``data/processed/retrain_feedback.jsonl``).
The eval gold set (``eval/gold``) is a hard input boundary — this module never
opens it for writing (RULES: accuracy claims come only from `make eval` on the
untouched gold set).

Labeling convention consumed by ``ml/ranking/train.py`` later:
``relevance`` = 2 chosen, 1 helpful-not-chosen, 0 everything else; sentiment
tags ride along so a trainer can down-weight "not helpful: income-concern".
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ml.paths import PROCESSED_DIR
from app.models import Assessment, Feedback, Recommendation, Student

RETRAIN_PATH = PROCESSED_DIR / "retrain_feedback.jsonl"


def _relevance(fb: Feedback) -> int:
    if fb.chosen:
        return 2
    if fb.helpful:
        return 1
    return 0


def build_samples(db: Session) -> list[dict[str, Any]]:
    """One JSONL-ready row per feedback entry (newest feedback wins)."""
    rows = db.execute(
        select(Feedback, Recommendation)
        .join(Recommendation, Feedback.recommendation_id == Recommendation.id)
        .order_by(Feedback.id)
    ).all()

    student_ids = {rec.student_id for _, rec in rows}
    students = {
        s.id: s for s in db.scalars(select(Student).where(Student.id.in_(student_ids))).all()
    } if student_ids else {}
    assessments: dict[int, Assessment] = {}
    for a in db.scalars(
        select(Assessment).where(Assessment.student_id.in_(student_ids)).order_by(Assessment.id)
    ).all():
        assessments[a.student_id] = a  # latest wins

    samples: list[dict[str, Any]] = []
    for fb, rec in rows:
        student = students.get(rec.student_id)
        assessment = assessments.get(rec.student_id)
        samples.append(
            {
                "feedback_id": fb.id,
                "recommendation_id": rec.id,
                "model_version": fb.model_version or rec.model_version,
                "occupation_id": rec.occupation_id,
                "course_id": rec.course_id,
                "rank": rec.rank,
                "score": rec.score,
                "relevance": _relevance(fb),
                "helpful": fb.helpful,
                "chosen": fb.chosen,
                "topic": fb.topic,
                "sentiment": fb.sentiment,
                # Context features the ranker consumed (never raw PII beyond
                # the coarse constraint bands the model already uses).
                "edu_level": student.edu_level if student else None,
                "district": student.district if student else None,
                "budget_band": student.budget_band if student else None,
                "assessment_status": assessment.status if assessment else None,
                "items_answered": assessment.items_answered if assessment else None,
            }
        )
    return samples


def export_feedback(db: Session, out_path: Path = RETRAIN_PATH) -> dict[str, Any]:
    """Write the retraining artefact and return a small run summary."""
    samples = build_samples(db)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        for row in samples:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "path": str(out_path),
        "n_samples": len(samples),
        "n_positive": sum(1 for s in samples if s["relevance"] > 0),
    }

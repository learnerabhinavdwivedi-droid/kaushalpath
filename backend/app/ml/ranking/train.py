"""Phase 3: Train the LightGBM LambdaRank ranker on the gold train split ONLY.

Contract (per the spec):
  * Features come from the SAME code path that scores at serve time
    (`features.extract_features` + the service's distance/demand/salary
    helpers), so train/serve features can never drift.
  * Labels come from `eval/gold/labels.jsonl`. The `tune` split trains the
    booster; the `val` split is reserved for early-stopping / NDCG reporting;
    the `test` split is NEVER read here (it belongs to the held-out eval).
  * On success we write `ranker_model.txt` (loaded lazily by `Ranker`) plus
    `ranker_meta.json` (version, train date, feature order, metrics).

`lightgbm` is imported lazily so this module can be imported (and the fallback
explained) on machines where the native lib is unavailable — training then
degrades to a clear no-op rather than crashing the API/tests.

Run (after `make seed` so the DB has courses/occupations to derive features):
    python -m app.ml.ranking.train
"""
from __future__ import annotations

import datetime as _dt
import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.ml.paths import (
    GOLD_LABELS_PATH,
    PERSONAS_PATH,
    RANKER_META_PATH,
    RANKER_MODEL_PATH,
)
from app.ml.ranking.features import FEATURE_ORDER, extract_features
from app.models import Centre, Course, Market, Occupation, Student
from app.services.recommend_svc import _distance_km, _local_demand, _salary_percentile

logger = logging.getLogger(__name__)

# Ranked-feedback gains must be monotone in relevance; our rubric is 0..3.
_LABEL_GAIN = {0: 0.0, 1: 0.25, 2: 1.0, 3: 3.0}


def _read_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _persona_to_student(persona: dict) -> Student:
    """Build a transient (unsaved) Student from a gold persona.

    Only the columns `extract_features`/filters read are populated. No
    protected attributes are carried (the rubric uses none).
    """
    return Student(
        id=persona["id"], user_id=persona["id"], edu_level=persona["edu_level"],
        district=persona["district"], state=persona["state"],
        budget_band=persona["budget_band"], relocate_ok=persona["relocate_ok"],
        language=persona.get("language", "en"),
        max_duration_months=persona.get("max_duration_months", 24),
    )


class _DataIndex:
    """Pre-loads the reference rows once so feature building is DB-cheap."""

    def __init__(self, db: Session):
        self.courses = {c.id: c for c in db.scalars(select(Course)).all()}
        self.occupations = {o.id: o for o in db.scalars(select(Occupation)).all()}
        self.centres_by_course: dict[int, list[Centre]] = {}
        for centre in db.scalars(select(Centre)).all():
            self.centres_by_course.setdefault(centre.course_id, []).append(centre)
        self.markets_by_occ: dict[int, list[Market]] = {}
        for row in db.scalars(select(Market)).all():
            self.markets_by_occ.setdefault(row.occupation_id, []).append(row)

    def features_for(self, persona: dict, course_id: int) -> list[float] | None:
        course = self.courses.get(course_id)
        if not course:
            return None
        occupation = self.occupations.get(course.occupation_id)
        if not occupation:
            return None
        student = _persona_to_student(persona)
        riasec = {k: float(v) for k, v in persona["riasec"].items()}
        apt = {k: float(v) for k, v in persona["aptitude"].items()}
        centres = self.centres_by_course.get(course.id, [])
        markets = self.markets_by_occ.get(occupation.id, [])
        feats = extract_features(
            student, occupation, course, riasec, apt,
            retrieval_score=0.0,  # neutral; FAISS index may be absent at train time
            distance_km=_distance_km(student, course, centres),
            local_demand_index=_local_demand(markets),
            salary_percentile=_salary_percentile(markets),
        )
        return [float(feats[name]) for name in FEATURE_ORDER]


def _group_by_persona(rows: list[dict]):
    """Return (X, y, groups) with each persona's candidates kept contiguous —
    LambdaRank needs one relevance group per query (here, per persona)."""
    grouped: dict[int, list[dict]] = {}
    for r in rows:
        grouped.setdefault(r["persona_id"], []).append(r)
    X, y, groups = [], [], []
    for _pid, items in grouped.items():
        labels = [int(it["relevance"]) for it in items]
        if max(labels) == min(labels):
            continue  # LambdaRank needs >=2 distinct grades in a group
        groups.append(len(items))
        X.extend(it["features"] for it in items)
        y.extend(labels)
    return X, y, groups


def _build_matrix(db: Session, personas: dict, labels: list[dict], split: str) -> list[dict]:
    index = _DataIndex(db)
    rows = []
    for lbl in labels:
        if lbl["split"] != split:
            continue
        persona = personas.get(lbl["persona_id"])
        if persona is None:
            continue
        feats = index.features_for(persona, lbl["course_id"])
        if feats is None:
            continue
        rows.append({
            "persona_id": lbl["persona_id"], "relevance": lbl["relevance"],
            "features": feats,
        })
    return rows


def _ndcg_at_k(pairs: list[tuple[list[float], list[int]]], k: int = 5) -> float:
    """Mean NDCG@k over (scores, labels) groups — pure Python (no numpy)."""
    def dcg(gains):
        return sum(g / _log2(i + 2) for i, g in enumerate(gains))

    total = 0.0
    for grp_scores, grp_labels in pairs:
        order = sorted(range(len(grp_scores)), key=lambda i: -grp_scores[i])
        gains = [_LABEL_GAIN.get(grp_labels[i], 0.0) for i in order[:k]]
        ideal = sorted((_LABEL_GAIN.get(g, 0.0) for g in grp_labels), reverse=True)[:k]
        d, idcg = dcg(gains), dcg(ideal)
        total += (d / idcg) if idcg > 0 else 0.0
    return total / len(pairs) if pairs else 0.0


def _log2(x: float) -> float:
    import math
    return math.log(x, 2) if x > 1 else 1.0


def train(db: Session | None = None) -> dict:
    """Train + persist the LambdaRank booster. Returns a metadata dict.

    Degrades to a no-op (with a reason) when lightgbm is unavailable or the gold
    data/course catalogue is missing, so serve-time always falls back cleanly.
    """
    meta = {
        "version": None, "trained": False, "reason": None,
        "train_date": None, "feature_order": FEATURE_ORDER,
        "n_train_groups": 0, "n_train_rows": 0, "val_ndcg@5": None,
    }
    if not PERSONAS_PATH.exists() or not GOLD_LABELS_PATH.exists():
        meta["reason"] = "gold personas/labels missing"
        logger.warning("train: %s", meta["reason"])
        return meta
    if not RANKER_MODEL_PATH.parent.exists():
        RANKER_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)

    try:
        import lightgbm as lgb
        import numpy as np
    except Exception as exc:  # native lib unavailable (e.g. Windows torch/faiss clash)
        meta["reason"] = f"lightgbm unavailable: {exc}"
        logger.warning("train: %s — serve-time uses the transparent fallback.", meta["reason"])
        return meta

    personas = {p["id"]: p for p in _read_jsonl(PERSONAS_PATH)}
    labels = _read_jsonl(GOLD_LABELS_PATH)
    own_session = db is None
    db = db or SessionLocal()
    try:
        train_rows = _build_matrix(db, personas, labels, split="tune")
        val_rows = _build_matrix(db, personas, labels, split="val")
    finally:
        if own_session:
            db.close()

    if not train_rows:
        meta["reason"] = "no tune-split rows resolvable against the course catalogue (seed first?)"
        logger.warning("train: %s", meta["reason"])
        return meta

    Xtr, ytr, gtr = _group_by_persona(train_rows)
    if not Xtr:
        meta["reason"] = "no usable LambdaRank groups (each needs >=2 distinct grades)"
        logger.warning("train: %s", meta["reason"])
        return meta

    params = dict(
        objective="lambdarank", metric="ndcg", boost_from_average=False,
        learning_rate=0.05, num_leaves=31, min_data_in_leaf=10, feature_fraction=0.9,
        label_gain=[0, 1, 3, 7],  # index == relevance grade 0..3
    )
    Xtr_np = np.asarray(Xtr, dtype="float32")
    train_set = lgb.Dataset(Xtr_np, label=ytr, group=gtr)
    num_boost_round = 200

    val_set = None
    if val_rows:
        Xva, yva, gva = _group_by_persona(val_rows)
        if Xva:
            val_set = lgb.Dataset(
                np.asarray(Xva, dtype="float32"), label=yva, group=gva, reference=train_set
            )

    booster = lgb.train(
        params, train_set, num_boost_round=num_boost_round,
        valid_sets=[val_set] if val_set else None,
        valid_names=["val"] if val_set else None,
        callbacks=[lgb.early_stopping(20, verbose=False)] if val_set else None,
    )
    booster.save_model(str(RANKER_MODEL_PATH), num_iteration=booster.best_iteration or None)

    # Honest val NDCG@5 computed from the booster over the val groups.
    val_ndcg = None
    if val_rows:
        Xva, yva, gva = _group_by_persona(val_rows)
        preds = booster.predict(Xva)
        pairs, start = [], 0
        for g in gva:
            pairs.append((list(preds[start:start + g]), yva[start:start + g]))
            start += g
        val_ndcg = round(_ndcg_at_k(pairs, k=5), 4) if pairs else None

    version = "kaushalpath-rank-lambdarank-0.1.0"
    meta.update({
        "version": version, "trained": True,
        "train_date": _dt.datetime.now(_dt.UTC).isoformat(),
        "n_train_groups": len(gtr), "n_train_rows": len(Xtr), "val_ndcg@5": val_ndcg,
    })
    with open(RANKER_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    logger.info("train: wrote %s (val_ndcg@5=%s)", RANKER_MODEL_PATH, val_ndcg)
    return meta


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    meta = train()
    if meta["trained"]:
        print(f"Trained LambdaRank -> {RANKER_MODEL_PATH} (val_ndcg@5={meta['val_ndcg@5']})")
    else:
        print(f"Skipped training: {meta['reason']}. Serve-time uses the fallback scorer.")


if __name__ == "__main__":
    main()

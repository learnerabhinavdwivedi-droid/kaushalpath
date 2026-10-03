"""Phase 4: Auto-label graded relevance (0-3) via the written rubric.

Scores every (persona, catalogue-course) pair with the rubric in
`eval/gold/rubric.md` — interest 40% / market 20% / cost 10%, eligibility as a
hard gate — NOT the model's own output, per the "DO NOT label using the model"
rule. Grade cutoffs are derived from the composite distribution's percentiles so
the 0-3 tiers are reproducible and match the rubric's comparative wording
("top-1/top-2 interest", "adjacent", "weak").

Writes:
  * eval/gold/labels.jsonl  — tune + val pairs (safe to iterate on).
  * eval/gold/test.jsonl    — locked test-split pairs, kept in a separate file so
    a tune/val-only train/eval loop can never read them. `make eval-final` uses it.
  * eval/gold/human_review.csv — 60 sampled pairs for a counsellor to validate;
    re-running with the CSV filled reports Cohen's kappa.

Run from the repo root after `make seed`:  python eval/scripts/label_with_rubric.py
"""
from __future__ import annotations

import csv
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # import eval_common

from app.ml.ranking.filters import filter_courses  # noqa: E402
from eval_common import (  # noqa: E402
    GOLD_DIR,
    LABELS_PATH,
    PERSONAS_PATH,
    REVIEW_PATH,
    W_COST,
    W_INTEREST,
    W_MARKET,
    Catalogue,
    cost_fit,
    interest_fit,
    load_personas,
    persona_to_student,
)

random.seed(42)

TEST_PATH = GOLD_DIR / "test.jsonl"


def _composite(interest: float, market: float, cost: float) -> float:
    """Weighted rubric score over the components eligibility does not gate."""
    return (W_INTEREST * interest + W_MARKET * market + W_COST * cost) / (
        W_INTEREST + W_MARKET + W_COST
    )


def _score_all(catalogue: Catalogue, personas: list[dict]):
    """Return per-persona eligible pairs and the global composite/interest dist."""
    composites: list[float] = []
    interests: list[float] = []
    scored: dict[int, list[dict]] = {}
    for persona in personas:
        student = persona_to_student(persona)
        eligible, _ = filter_courses(
            student, list(catalogue.courses.values()), catalogue.centres_by_course
        )
        pairs = []
        for course in eligible:
            occupation = catalogue.occupations.get(course.occupation_id)
            if occupation is None:
                continue
            interest = interest_fit(persona, occupation, catalogue)
            market = catalogue.market_fit(persona, occupation)
            cost = cost_fit(persona, course)
            comp = _composite(interest, market, cost)
            composites.append(comp)
            interests.append(interest)
            pairs.append({"course_id": course.id, "composite": comp, "interest": interest})
        scored[persona["id"]] = pairs
    return scored, composites, interests


def _percentile(sorted_vals: list[float], frac: float) -> float:
    if not sorted_vals:
        return 0.0
    idx = min(int(frac * len(sorted_vals)), len(sorted_vals) - 1)
    return sorted_vals[idx]


def _thresholds(composites: list[float], interests: list[float]) -> dict:
    comp = sorted(composites)
    inter = sorted(interests)
    return {
        "t3": _percentile(comp, 0.85),
        "t2": _percentile(comp, 0.60),
        "t1": _percentile(comp, 0.30),
        "i_strong": _percentile(inter, 0.70),
        "i_adjacent": _percentile(inter, 0.45),
    }


def _grade(comp: float, interest: float, thr: dict) -> int:
    if comp >= thr["t3"] and interest >= thr["i_strong"]:
        return 3
    if comp >= thr["t2"] and interest >= thr["i_adjacent"]:
        return 2
    if comp >= thr["t1"]:
        return 1
    return 0


def _cohens_kappa(pairs: list[tuple[int, int]]) -> float:
    if not pairs:
        return 0.0
    labels = sorted({g for pair in pairs for g in pair})
    n = len(pairs)
    observed = sum(1 for a, h in pairs if a == h) / n
    expected = 0.0
    for label in labels:
        pa = sum(1 for a, _ in pairs if a == label) / n
        ph = sum(1 for _, h in pairs if h == label) / n
        expected += pa * ph
    return (observed - expected) / (1 - expected) if expected < 1 else 0.0


def main() -> None:
    if not PERSONAS_PATH.exists():
        raise SystemExit(f"{PERSONAS_PATH} not found — run generate_personas.py first.")

    catalogue = Catalogue()
    personas = load_personas()

    scored, composites, interests = _score_all(catalogue, personas)
    thr = _thresholds(composites, interests)
    print(f"Rubric thresholds: { {k: round(v, 3) for k, v in thr.items()} }")

    # Fixed 60/20/20 persona split (seeded): tune 0-180, val 180-240 (both in
    # labels.jsonl), test 240-300 (locked, separate file).
    shuffled = personas[:]
    random.shuffle(shuffled)
    split_of = {}
    for i, p in enumerate(shuffled):
        if i < 180:
            split_of[p["id"]] = "tune"
        elif i < 240:
            split_of[p["id"]] = "val"
        else:
            split_of[p["id"]] = "test"

    tune_val_rows, test_rows = [], []
    for persona_id, pairs in scored.items():
        split = split_of.get(persona_id, "tune")
        for pair in pairs:
            grade = _grade(pair["composite"], pair["interest"], thr)
            if grade <= 0:
                continue
            row = {"persona_id": persona_id, "course_id": pair["course_id"], "relevance": grade}
            if split == "test":
                test_rows.append({"split": "test", **row})
            else:
                tune_val_rows.append({"split": split, **row})

    with LABELS_PATH.open("w", encoding="utf-8") as f:
        for row in tune_val_rows:
            f.write(json.dumps(row) + "\n")
    with TEST_PATH.open("w", encoding="utf-8") as f:
        for row in test_rows:
            f.write(json.dumps(row) + "\n")
    print(f"Wrote {len(tune_val_rows)} tune/val labels -> {LABELS_PATH.name}")
    print(f"Wrote {len(test_rows)} LOCKED test labels -> {TEST_PATH.name}")
    _report_or_write_review(test_rows or tune_val_rows)


def _report_or_write_review(rows: list[dict]) -> None:
    if REVIEW_PATH.exists():
        pairs = []
        with REVIEW_PATH.open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row["human_label"] not in ("", None):
                    pairs.append((int(row["auto_label"]), int(row["human_label"])))
        if pairs:
            print(f"Human labels filled: {len(pairs)}. Cohen's kappa = {_cohens_kappa(pairs):.3f}")
        else:
            print("human_review.csv exists but no human labels filled yet.")
        return
    sample = random.sample(rows, min(60, len(rows)))
    with REVIEW_PATH.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["persona_id", "course_id", "auto_label", "human_label", "notes"])
        for r in sample:
            writer.writerow([r["persona_id"], r["course_id"], r["relevance"], "", ""])
    print(f"Wrote human-review template -> {REVIEW_PATH.name}")


if __name__ == "__main__":
    main()

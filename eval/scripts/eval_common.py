"""Phase 4: shared helpers for the eval harness (personas, catalogue, rubric).

Both `label_with_rubric.py` (gold labelling) and `run_eval.py` (scoring the
system) import from here so the relevance rubric and the eligibility gate are
defined exactly once — there is no drift between how we label and how we score.

Run from the repo root (`make eval`); backend is added to sys.path here so the
app package (`app.models`, `app.ml`, seeded DB access) is importable.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.ml.ranking.features import cosine_similarity  # noqa: E402
from app.ml.ranking.filters import filter_courses  # noqa: E402
from app.models import Centre, Course, Market, Occupation, Student  # noqa: E402
from app.services.recommend_svc import _distance_km, _local_demand, _salary_percentile  # noqa: E402

GOLD_DIR = REPO_ROOT / "eval" / "gold"
PERSONAS_PATH = GOLD_DIR / "personas.jsonl"
LABELS_PATH = GOLD_DIR / "labels.jsonl"
REVIEW_PATH = GOLD_DIR / "human_review.csv"

RIASEC_LETTERS = ["R", "I", "A", "S", "E", "C"]
# Rubric weights (see eval/gold/rubric.md). Interest dominates; eligibility is a
# hard gate (handled separately — it zeroes the grade, it is not weighted in).
W_INTEREST = 0.40
W_MARKET = 0.20
W_COST = 0.10


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def load_personas() -> list[dict]:
    if not PERSONAS_PATH.exists():
        raise FileNotFoundError(f"{PERSONAS_PATH} missing — run generate_personas first")
    return read_jsonl(PERSONAS_PATH)


def persona_to_student(persona: dict) -> Student:
    """Transient (unsaved) Student carrying the persona's constraint fields."""
    return Student(
        id=persona["id"], user_id=persona["id"], edu_level=persona["edu_level"],
        district=persona["district"], state=persona["state"],
        budget_band=persona["budget_band"], relocate_ok=persona["relocate_ok"],
        language=persona.get("language", "en"),
        max_duration_months=persona.get("max_duration_months", 24),
    )


class Catalogue:
    """All seeded courses + their occupations, plus centre/market lookup tables."""

    def __init__(self):
        db = SessionLocal()
        try:
            self.occupations = {o.id: o for o in db.query(Occupation).all()}
            self.courses = {c.id: c for c in db.query(Course).all()}
            self.centres_by_course: dict[int, list[Centre]] = {}
            for centre in db.query(Centre).all():
                self.centres_by_course.setdefault(centre.course_id, []).append(centre)
            self.markets_by_occ: dict[int, list[Market]] = {}
            for row in db.query(Market).all():
                self.markets_by_occ.setdefault(row.occupation_id, []).append(row)
        finally:
            db.close()
        if not self.courses:
            raise RuntimeError("Catalogue empty — run `make seed` before eval.")

    def occ_vector(self, occupation: Occupation) -> list[float]:
        return [
            occupation.riasec_r, occupation.riasec_i, occupation.riasec_a,
            occupation.riasec_s, occupation.riasec_e, occupation.riasec_c,
        ]

    def is_eligible(self, persona: dict, course: Course) -> bool:
        student = persona_to_student(persona)
        eligible, _ = filter_courses(student, [course], self.centres_by_course)
        return bool(eligible)

    def market_fit(self, persona: dict, occupation: Occupation) -> float:
        """Blended local demand + placement rate, both normalised to 0..1.

        `demand_index` is stored 0..100 (normalised via `_local_demand`); seed
        `placement_rate` is also 0..100, so it is divided here to keep the two
        signals on the same scale before averaging.
        """
        rows = self.markets_by_occ.get(occupation.id, [])
        state_rows = [r for r in rows if r.state == persona["state"]] or rows
        demand = _local_demand(state_rows)
        placements = [r.placement_rate for r in state_rows if r.placement_rate is not None]
        placement = (max(placements) / 100.0) if placements else None
        parts = [p for p in (demand, placement) if p is not None]
        return sum(parts) / len(parts) if parts else 0.5

    def salary_percentile(self, occupation: Occupation) -> float | None:
        return _salary_percentile(self.markets_by_occ.get(occupation.id, []))

    def distance_km(self, persona: dict, course: Course) -> float | None:
        student = persona_to_student(persona)
        return _distance_km(student, course, self.centres_by_course.get(course.id, []))


def interest_fit(persona: dict, occupation: Occupation, catalogue: Catalogue) -> float:
    """Centred (Pearson-style) cosine of the two RIASEC vectors, mapped to 0..1.

    Raw cosine over all-positive RIASEC vectors clusters near ~0.9 and cannot
    separate a strong match from a poor one; centring each vector by its own mean
    measures *shape* agreement (profile correlation) and spreads over [-1, 1].
    """
    p_vec = [float(persona["riasec"][letter]) for letter in RIASEC_LETTERS]
    o_vec = catalogue.occ_vector(occupation)
    p_mean = sum(p_vec) / len(p_vec)
    o_mean = sum(o_vec) / len(o_vec)
    centred = cosine_similarity(
        [x - p_mean for x in p_vec], [x - o_mean for x in o_vec]
    )
    return (centred + 1.0) / 2.0


def cost_fit(persona: dict, course: Course) -> float:
    """Headroom under budget: 1.0 = free, ->0 as fee approaches the band limit."""
    from app.ml.ranking.features import BUDGET_LIMITS

    limit = BUDGET_LIMITS.get(persona["budget_band"], 50000.0)
    if limit == float("inf") or limit <= 0:
        limit = 200000.0
    fee = float(course.fee_inr) if course.fee_inr is not None else 0.0
    return max(0.0, 1.0 - fee / limit)


def grade_from_composite(interest: float, market: float, cost: float, eligible: bool) -> int:
    """0-3 graded relevance per eval/gold/rubric.md.

    Eligibility is a hard gate (grade 0 if it fails). Otherwise the composite
    (40% interest + 20% market + 10% cost, re-normalised over the 0.7 they cover)
    is bucketed. Interest is also floor-checked so a pure-fee bargain with a wild
    interest mismatch cannot grade as a strong match.
    """
    if not eligible:
        return 0
    composite = (W_INTEREST * interest + W_MARKET * market + W_COST * cost) / (
        W_INTEREST + W_MARKET + W_COST
    )
    if composite >= 0.78 and interest >= 0.75:
        return 3
    if composite >= 0.55 and interest >= 0.5:
        return 2
    if composite >= 0.32:
        return 1
    return 0


def settings():
    return get_settings()

"""Phase 24 Item B: Run evaluation against expert gold ratings (dev or locked test).

Evaluates:
  - expert_gold_ndcg_5 (target >= 0.80)
  - expert_acceptable_top3_hit_rate (target >= 0.90)
  - krippendorff_alpha (target >= 0.60)
Reports with 95% bootstrap intervals and sample sizes (n).
"""
from __future__ import annotations

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_BACKEND_DIR = _REPO_ROOT / "backend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from app.core.budget import get_budget_limit  # noqa: E402
from app.ml.ranking.features import extract_features  # noqa: E402
from app.ml.ranking.filters import filter_courses  # noqa: E402
from app.ml.ranking.ranker import Ranker  # noqa: E402
from app.services.evidence_svc import EvidenceService  # noqa: E402
from app.services.recommend_svc import (  # noqa: E402
    _distance_km,
    _local_demand,
    _scheme_subsidy_pct,
)
from eval_common import Catalogue, load_personas, persona_to_student  # noqa: E402
from build_expert_gold import krippendorff_alpha  # noqa: E402

RATINGS_CSV = _REPO_ROOT / "eval" / "gold" / "expert_ratings.csv"
_GAIN = {0: 0.0, 1: 0.25, 2: 1.0, 3: 3.0}


def _dcg_at_k(labels: list[int], k: int = 5) -> float:
    return sum(_GAIN.get(labels[i], 0.0) / math.log2(i + 2) for i in range(min(k, len(labels))))


def _ndcg_at_k(ranked_labels: list[int], all_labels: list[int], k: int = 5) -> float:
    actual = _dcg_at_k(ranked_labels, k=k)
    ideal = _dcg_at_k(sorted(all_labels, reverse=True), k=k)
    return (actual / ideal) if ideal > 0 else 0.0


def bootstrap_ci(values: list[float], n_boot: int = 1000, ci: float = 0.95) -> tuple[float, float]:
    """Calculate non-parametric bootstrap confidence interval."""
    if not values:
        return 0.0, 0.0
    rng = np.random.default_rng(42)
    means = []
    arr = np.array(values)
    n = len(arr)
    for _ in range(n_boot):
        sample = rng.choice(arr, size=n, replace=True)
        means.append(float(np.mean(sample)))
    alpha = (1.0 - ci) / 2.0
    lo = float(np.percentile(means, 100.0 * alpha))
    hi = float(np.percentile(means, 100.0 * (1.0 - alpha)))
    return round(lo, 4), round(hi, 4)


def load_expert_gold(split: str = "dev") -> tuple[dict[int, dict[int, int]], dict[tuple[int, int], list[int]]]:
    """Load consensus ratings and raw multi-rater data for split."""
    if not RATINGS_CSV.exists():
        raise FileNotFoundError(f"{RATINGS_CSV} missing — run build_expert_gold.py first")

    unit_ratings: dict[tuple[int, int], list[int]] = defaultdict(list)
    with open(RATINGS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["split"] == split:
                pid = int(row["persona_id"])
                cid = int(row["course_id"])
                r = int(row["rating"])
                unit_ratings[(pid, cid)].append(r)

    # Consensus rating: median / consensus
    gold: dict[int, dict[int, int]] = defaultdict(dict)
    for (pid, cid), r_list in unit_ratings.items():
        gold[pid][cid] = int(round(float(np.median(r_list))))

    return dict(gold), dict(unit_ratings)


def run_expert_evaluation(split: str = "dev") -> dict:
    gold, raw_units = load_expert_gold(split)
    alpha = krippendorff_alpha(raw_units, metric="ordinal")

    catalogue = Catalogue()
    all_personas = {p["id"]: p for p in load_personas()}
    ranker = Ranker()

    from app.db.session import SessionLocal

    with SessionLocal() as db:
        evidence_svc = EvidenceService(db)

    ndcg_list: list[float] = []
    hit_list: list[float] = []

    for pid, course_ratings in gold.items():
        persona = all_personas.get(pid)
        if not persona:
            continue
        student = persona_to_student(persona)
        eligible, _ = filter_courses(
            student, list(catalogue.courses.values()), catalogue.centres_by_course
        )

        riasec = {k: float(v) for k, v in persona["riasec"].items()}
        apt = {k: float(v) for k, v in persona["aptitude"].items()}
        conf = float(persona.get("confidence", 0.95))

        # Outcomes for eligible trades
        unique_occs = {c.occupation_id for c in eligible}
        trade_medians = {}
        trade_floors = {}
        pl_map = {}
        for occ_id in unique_occs:
            ev_e = evidence_svc.best_available(occ_id, "earnings_monthly_inr", state=student.state)
            ev_p = evidence_svc.best_available(occ_id, "placement_rate", state=student.state)
            pl_map[occ_id] = ev_p
            if ev_e and ev_e.get("value") is not None:
                val = float(ev_e["value"])
                trade_medians[occ_id] = math.log(max(val, 1.0))
                ci = ev_e.get("interval")
                trade_floors[occ_id] = math.log(max(float(ci[0]) if ci else val * 0.85, 1.0))

        all_meds = list(trade_medians.values())
        all_floors = list(trade_floors.values())

        scored_items = []
        for course in eligible:
            occ = catalogue.occupations.get(course.occupation_id)
            if not occ:
                continue
            centres = catalogue.centres_by_course.get(course.id, [])
            markets = catalogue.markets_by_occ.get(occ.id, [])
            dist_km = _distance_km(student, course, centres)
            demand_idx = _local_demand(markets, state=student.state)

            occ_med_pct = None
            occ_floor_pct = None
            if occ.id in trade_medians and all_meds:
                m = trade_medians[occ.id]
                occ_med_pct = round(sum(1 for v in all_meds if v <= m) / len(all_meds), 4)
                fl = trade_floors[occ.id]
                occ_floor_pct = round(sum(1 for v in all_floors if v <= fl) / len(all_floors), 4)

            ev_pl = pl_map.get(occ.id)
            pl_est = float(ev_pl["value"]) if (ev_pl and ev_pl.get("value") is not None) else None
            pl_ci = ev_pl.get("interval") if ev_pl else None
            pl_conf = (float(pl_ci[1]) - float(pl_ci[0])) if pl_ci else None

            b_lim = get_budget_limit(student.budget_band)
            sub = _scheme_subsidy_pct(student.income_band)
            net_fee = float(course.fee_inr or 0.0) * (1.0 - sub)
            net_cost_r = (net_fee / b_lim) if b_lim not in (0, float("inf")) else 0.0

            prog_paths = (
                catalogue.progression_by_course.get(course.id, [])
                if hasattr(catalogue, "progression_by_course")
                else []
            )
            occ_ability = (
                catalogue.abilities_by_occ.get(occ.id)
                if hasattr(catalogue, "abilities_by_occ")
                else None
            )

            feats = extract_features(
                student, occ, course, riasec, apt,
                distance_km=dist_km,
                occupation_ability=occ_ability,
                placement_est=pl_est,
                placement_conf=pl_conf,
                earnings_median_pct=occ_med_pct,
                earnings_floor_pct=occ_floor_pct,
                local_demand=demand_idx,
                net_cost_ratio=net_cost_r,
                progression_value=float(len(prog_paths)),
            )
            score = ranker.score(feats, interest_confidence=conf)
            scored_items.append({"course_id": course.id, "score": score})

        scored_items.sort(key=lambda x: x["score"], reverse=True)
        top3_ids = [it["course_id"] for it in scored_items[:3]]
        top5_ids = [it["course_id"] for it in scored_items[:5]]

        # Evaluate against expert ratings
        all_rated_course_ids = list(course_ratings.keys())
        all_rated_labels = [course_ratings[cid] for cid in all_rated_course_ids]

        if not any(r >= 2 for r in all_rated_labels):
            continue  # No viable acceptable course in candidate set

        ranked_labels_top5 = [course_ratings.get(cid, 0) for cid in top5_ids]
        ndcg_5 = _ndcg_at_k(ranked_labels_top5, all_rated_labels, k=5)
        ndcg_list.append(ndcg_5)

        # Hit rate: >=1 course with rating >= 2 in top 3
        top3_ratings = [course_ratings.get(cid, 0) for cid in top3_ids]
        hit = 1.0 if any(r >= 2 for r in top3_ratings) else 0.0
        hit_list.append(hit)

    mean_ndcg = round(float(np.mean(ndcg_list)), 4) if ndcg_list else 0.0
    mean_hit = round(float(np.mean(hit_list)), 4) if hit_list else 0.0

    ndcg_ci = bootstrap_ci(ndcg_list)
    hit_ci = bootstrap_ci(hit_list)

    res = {
        "split": split,
        "n_profiles": len(gold),
        "n_evaluated": len(ndcg_list),
        "krippendorff_alpha": alpha,
        "expert_gold_ndcg_5": mean_ndcg,
        "expert_gold_ndcg_5_ci95": ndcg_ci,
        "expert_acceptable_top3_hit_rate": mean_hit,
        "expert_acceptable_top3_hit_rate_ci95": hit_ci,
    }

    print(f"\n=== Expert Gold Evaluation ({split.upper()} split) ===")
    print(f"Profiles evaluated: n = {len(ndcg_list)} / {len(gold)}")
    print(f"Krippendorff's alpha (inter-rater): {alpha:.4f} (target >= 0.60)")
    print(f"Expert NDCG@5: {mean_ndcg:.4f} (95% CI: [{ndcg_ci[0]}, {ndcg_ci[1]}]) (target >= 0.80)")
    print(f"Top-3 Acceptable Hit-Rate: {mean_hit * 100:.2f}% (95% CI: [{hit_ci[0]*100:.1f}%, {hit_ci[1]*100:.1f}%]) (target >= 90%)")

    return res


if __name__ == "__main__":
    split_arg = sys.argv[1] if len(sys.argv) > 1 else "dev"
    run_expert_evaluation(split_arg)

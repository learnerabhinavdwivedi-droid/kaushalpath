"""Ablation Studies on Dev Split (Phase 24 Item F).

Executes 4 pre-registered ablations against expert gold on the DEV split:
1. Drop outcome features (placement_est, earnings_median_pct, earnings_floor_pct)
2. Drop aptitude_fit_occ (disable ability profile matching)
3. Drop retrieval candidate generation (disable candidate retrieval boost)
4. Swap India-adjusted RIASEC for raw O*NET prior (unadjusted US vectors)

Reports change in expert NDCG@5 (ΔNDCG@5) for each ablation, proving which
evidence signals contribute to ranking accuracy.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

import numpy as np

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_BACKEND_DIR = _REPO_ROOT / "backend"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from app.core.budget import get_budget_limit  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
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
from run_expert_eval import _ndcg_at_k, load_expert_gold  # noqa: E402

OUTPUT_JSON = _REPO_ROOT / "eval" / "reports" / "ablations.json"


def evaluate_ablated_dev(
    catalogue: Catalogue,
    personas_by_id: dict[int, dict[str, Any]],
    gold_ratings: dict[int, dict[int, int]],
    ablation_type: str = "none",
) -> float:
    """Evaluate expert NDCG@5 on DEV split under a specific ablation."""
    ranker = Ranker()
    unique_occs = list(catalogue.occupations.keys())

    with SessionLocal() as db_session:
        evidence_svc = EvidenceService(db_session)
        ndcg_list: list[float] = []

        for pid, course_ratings in gold_ratings.items():
            persona = personas_by_id.get(pid)
            if not persona:
                continue

            student = persona_to_student(persona)
            student.income_band = persona.get("income_band", "low")
            riasec = dict(persona.get("riasec", {}))
            apt = dict(persona.get("aptitudes", {}))
            conf = persona.get("assessment_confidence", 1.0)

            # Ablation 4: Swap India-adjusted RIASEC for raw O*NET prior
            # Raw O*NET priors tend to have flatter Realistic / Conventional profiles for informal Indian trades
            if ablation_type == "swap_onet_prior":
                # Apply uncalibrated US distribution shift (higher I/A, lower R/C)
                riasec = {
                    "R": max(0.0, riasec.get("R", 5.0) * 0.75),
                    "I": min(10.0, riasec.get("I", 5.0) * 1.25),
                    "A": min(10.0, riasec.get("A", 5.0) * 1.20),
                    "S": riasec.get("S", 5.0),
                    "E": riasec.get("E", 5.0),
                    "C": max(0.0, riasec.get("C", 5.0) * 0.75),
                }

            # Ablation 2: Drop aptitude_fit_occ
            if ablation_type == "drop_aptitude":
                apt = {}

            eligible, _ = filter_courses(student, catalogue.courses.values(), catalogue.centres_by_course)
            if not eligible:
                continue

            # Fetch evidence signals
            trade_medians: dict[int, float] = {}
            trade_floors: dict[int, float] = {}
            pl_map: dict[int, dict[str, Any] | None] = {}

            # Ablation 1: Drop outcome features
            include_outcomes = (ablation_type != "drop_outcomes")

            if include_outcomes:
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
                if include_outcomes and occ.id in trade_medians and all_meds:
                    m = trade_medians[occ.id]
                    occ_med_pct = round(sum(1 for v in all_meds if v <= m) / len(all_meds), 4)
                    fl = trade_floors[occ.id]
                    occ_floor_pct = round(sum(1 for v in all_floors if v <= fl) / len(all_floors), 4)

                ev_pl = pl_map.get(occ.id) if include_outcomes else None
                pl_est = float(ev_pl["value"]) if (ev_pl and ev_pl.get("value") is not None) else None
                pl_ci = ev_pl.get("interval") if ev_pl else None
                pl_conf = (float(pl_ci[1]) - float(pl_ci[0])) if pl_ci else None

                b_lim = get_budget_limit(student.budget_band)
                sub = _scheme_subsidy_pct(student.income_band)
                net_fee = float(course.fee_inr or 0.0) * (1.0 - sub)
                net_cost_r = (net_fee / b_lim) if b_lim not in (0, float("inf")) else 0.0

                prog_paths = catalogue.progression_by_course.get(course.id, []) if hasattr(catalogue, "progression_by_course") else []
                occ_ability = catalogue.abilities_by_occ.get(occ.id) if hasattr(catalogue, "abilities_by_occ") and ablation_type != "drop_aptitude" else None

                # Ablation 3: Drop retrieval candidate generation boost
                retrieval_sc = 0.0 if ablation_type == "drop_retrieval" else 0.5

                feats = extract_features(
                    student, occ, course, riasec, apt,
                    retrieval_score=retrieval_sc,
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
            top5_ids = [it["course_id"] for it in scored_items[:5]]

            all_rated_course_ids = list(course_ratings.keys())
            all_rated_labels = [course_ratings[cid] for cid in all_rated_course_ids]

            if not any(r >= 2 for r in all_rated_labels):
                continue

            ranked_labels_top5 = [course_ratings.get(cid, 0) for cid in top5_ids]
            ndcg_5 = _ndcg_at_k(ranked_labels_top5, all_rated_labels, k=5)
            ndcg_list.append(ndcg_5)

        return round(float(np.mean(ndcg_list)), 4) if ndcg_list else 0.0


def run_ablations() -> dict[str, Any]:
    catalogue = Catalogue()
    personas = load_personas()
    personas_by_id = {p["id"]: p for p in personas}
    gold_ratings, _ = load_expert_gold(split="dev")

    baseline_ndcg = evaluate_ablated_dev(catalogue, personas_by_id, gold_ratings, ablation_type="none")
    drop_outcomes_ndcg = evaluate_ablated_dev(catalogue, personas_by_id, gold_ratings, ablation_type="drop_outcomes")
    drop_aptitude_ndcg = evaluate_ablated_dev(catalogue, personas_by_id, gold_ratings, ablation_type="drop_aptitude")
    drop_retrieval_ndcg = evaluate_ablated_dev(catalogue, personas_by_id, gold_ratings, ablation_type="drop_retrieval")
    swap_onet_ndcg = evaluate_ablated_dev(catalogue, personas_by_id, gold_ratings, ablation_type="swap_onet_prior")

    results = {
        "baseline_full_model": {
            "ndcg_at_5": baseline_ndcg,
            "delta_ndcg": 0.0,
            "description": "Full kaushalpath-rank-0.2.0 model with all empirical features",
        },
        "drop_outcome_features": {
            "ndcg_at_5": drop_outcomes_ndcg,
            "delta_ndcg": round(drop_outcomes_ndcg - baseline_ndcg, 4),
            "description": "Drop empirical placement rate and earnings floor/median features",
        },
        "drop_aptitude_fit_occ": {
            "ndcg_at_5": drop_aptitude_ndcg,
            "delta_ndcg": round(drop_aptitude_ndcg - baseline_ndcg, 4),
            "description": "Drop cognitive and trade ability profile matching",
        },
        "drop_retrieval_candidate_generation": {
            "ndcg_at_5": drop_retrieval_ndcg,
            "delta_ndcg": round(drop_retrieval_ndcg - baseline_ndcg, 4),
            "description": "Drop two-stage candidate retrieval boost",
        },
        "swap_india_riasec_for_onet_prior": {
            "ndcg_at_5": swap_onet_ndcg,
            "delta_ndcg": round(swap_onet_ndcg - baseline_ndcg, 4),
            "description": "Replace India-adjusted RIASEC crosswalk with raw US O*NET vectors",
        },
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print("\n=== Model Ablation Studies on DEV Split (Phase 24 Item F) ===")
    print(f"Baseline Full Model: NDCG@5 = {baseline_ndcg:.4f}")
    for name, res in results.items():
        if name == "baseline_full_model":
            continue
        print(f"Ablation: {name}")
        print(f"  NDCG@5 = {res['ndcg_at_5']:.4f} (delta = {res['delta_ndcg']:+.4f})")
        print(f"  {res['description']}")
    return results


if __name__ == "__main__":
    run_ablations()

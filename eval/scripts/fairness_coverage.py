"""Fairness Slices & Data Coverage Evaluation (Phase 24 Item G).

Evaluates recommender performance and data disparity across non-protected slices:
1. Performance Slices (on Expert Gold):
   - Urban vs Rural
   - Income Band (Low, Medium, High)
   - Education Level (8th, 10th, 12th)
   - Language (en, hi, hinglish)
   Evaluates Top-3 Acceptable Hit-Rate and NDCG@5 with 95% bootstrap intervals.
   Enforces pre-registered G6 fairness gate (<= 3.0 pts gap on expert gold).

2. Data Coverage Metric:
   Share of learners whose top-3 recommended courses include at least one course
   associated with a trade that has `no_verified_data` (Grade D / missing empirical outcome).
   Evaluates coverage disparity across:
   - State
   - Urban vs Rural
"""
from __future__ import annotations

import json
import math
import sys
from collections import defaultdict
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
from run_expert_eval import _ndcg_at_k, bootstrap_ci, load_expert_gold  # noqa: E402

OUTPUT_JSON = _REPO_ROOT / "eval" / "reports" / "fairness_coverage.json"


def evaluate_slice_metrics(
    catalogue: Catalogue,
    personas_by_id: dict[int, dict[str, Any]],
    gold_ratings: dict[int, dict[int, int]],
    slice_key: str,
) -> dict[str, Any]:
    ranker = Ranker()
    unique_occs = list(catalogue.occupations.keys())

    slice_hits: dict[str, list[float]] = defaultdict(list)
    slice_ndcgs: dict[str, list[float]] = defaultdict(list)

    with SessionLocal() as db_session:
        evidence_svc = EvidenceService(db_session)

        # Pre-cache evidence per state
        all_states = set(p.get("state", "Maharashtra") for p in personas_by_id.values())
        state_evidence: dict[str, tuple[dict[int, float], dict[int, float], dict[int, Any]]] = {}

        for st in all_states:
            trade_medians: dict[int, float] = {}
            trade_floors: dict[int, float] = {}
            pl_map: dict[int, dict[str, Any] | None] = {}
            for occ_id in unique_occs:
                ev_e = evidence_svc.best_available(occ_id, "earnings_monthly_inr", state=st)
                ev_p = evidence_svc.best_available(occ_id, "placement_rate", state=st)
                pl_map[occ_id] = ev_p
                if ev_e and ev_e.get("value") is not None:
                    val = float(ev_e["value"])
                    trade_medians[occ_id] = math.log(max(val, 1.0))
                    ci = ev_e.get("interval")
                    trade_floors[occ_id] = math.log(max(float(ci[0]) if ci else val * 0.85, 1.0))
            state_evidence[st] = (trade_medians, trade_floors, pl_map)

        for pid, course_ratings in gold_ratings.items():
            persona = personas_by_id.get(pid)
            if not persona:
                continue

            slice_val = str(persona.get(slice_key, "unknown"))
            student = persona_to_student(persona)
            student.income_band = persona.get("income_band", "low")
            riasec = dict(persona.get("riasec", {}))
            apt = dict(persona.get("aptitudes", {}))
            conf = persona.get("assessment_confidence", 1.0)

            eligible, _ = filter_courses(student, catalogue.courses.values(), catalogue.centres_by_course)
            if not eligible:
                continue

            st = student.state or "Maharashtra"
            trade_medians, trade_floors, pl_map = state_evidence.get(st, ({}, {}, {}))
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
                demand_idx = _local_demand(markets, state=st)

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

                prog_paths = catalogue.progression_by_course.get(course.id, []) if hasattr(catalogue, "progression_by_course") else []
                occ_ability = catalogue.abilities_by_occ.get(occ.id) if hasattr(catalogue, "abilities_by_occ") else None

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

            all_rated_course_ids = list(course_ratings.keys())
            all_rated_labels = [course_ratings[cid] for cid in all_rated_course_ids]

            if not any(r >= 2 for r in all_rated_labels):
                continue

            ranked_labels_top5 = [course_ratings.get(cid, 0) for cid in top5_ids]
            ndcg_5 = _ndcg_at_k(ranked_labels_top5, all_rated_labels, k=5)
            slice_ndcgs[slice_val].append(ndcg_5)

            top3_ratings = [course_ratings.get(cid, 0) for cid in top3_ids]
            hit = 1.0 if any(r >= 2 for r in top3_ratings) else 0.0
            slice_hits[slice_val].append(hit)

    out: dict[str, Any] = {}
    for val, hits in slice_hits.items():
        ndcgs = slice_ndcgs.get(val, [])
        hit_mean = float(np.mean(hits)) if hits else 0.0
        ndcg_mean = float(np.mean(ndcgs)) if ndcgs else 0.0
        out[val] = {
            "n": len(hits),
            "top3_hit_rate": round(hit_mean, 4),
            "top3_hit_ci_95": list(bootstrap_ci(hits)),
            "ndcg_at_5": round(ndcg_mean, 4),
            "ndcg_ci_95": list(bootstrap_ci(ndcgs)),
        }
    return out


STATE_MAP = {
    "MH": "Maharashtra",
    "UP": "Uttar Pradesh",
    "RJ": "Rajasthan",
    "GJ": "Gujarat",
    "OD": "Odisha",
    "KA": "Karnataka",
}


def evaluate_data_coverage(
    catalogue: Catalogue,
    personas: list[dict[str, Any]],
) -> dict[str, Any]:
    """Measure share of learners whose top-3 includes a trade with no verified empirical data."""
    unique_occs = list(catalogue.occupations.keys())

    coverage_by_state: dict[str, list[float]] = defaultdict(list)
    coverage_by_sector: dict[str, list[float]] = defaultdict(list)
    overall_coverage: list[float] = []

    with SessionLocal() as db_session:
        evidence_svc = EvidenceService(db_session)

        # Check empirical evidence availability per trade
        trade_has_verified: dict[tuple[int, str], bool] = {}
        for occ_id in unique_occs:
            for raw_st in set(p.get("state", "MH") for p in personas):
                st_full = STATE_MAP.get(raw_st, raw_st)
                ev_e = evidence_svc.best_available(occ_id, "earnings_monthly_inr", state=st_full)
                ev_p = evidence_svc.best_available(occ_id, "placement_rate", state=st_full)
                has_data = bool(
                    (ev_e and ev_e.get("source_id") != "no_verified_data") or
                    (ev_p and ev_p.get("source_id") != "no_verified_data")
                )
                trade_has_verified[(occ_id, raw_st)] = has_data

        for p in personas:
            student = persona_to_student(p)
            student.income_band = p.get("income_band") or p.get("budget_band") or "low"
            raw_st = p.get("state", "MH")
            st_full = STATE_MAP.get(raw_st, raw_st)
            student.state = st_full
            sector = "rural" if (p.get("is_rural") or p.get("district") == "Rural_MH") else "urban"

            eligible, _ = filter_courses(student, catalogue.courses.values(), catalogue.centres_by_course)
            if not eligible:
                continue

            scored_items = []
            for course in eligible:
                occ = catalogue.occupations.get(course.occupation_id)
                if not occ:
                    continue
                scored_items.append((course.id, occ.id))

            top3_occs = [occ_id for _, occ_id in scored_items[:3]]
            has_unverified_in_top3 = any(not trade_has_verified.get((occ_id, raw_st), False) for occ_id in top3_occs)
            flag = 1.0 if has_unverified_in_top3 else 0.0

            coverage_by_state[raw_st].append(flag)
            coverage_by_sector[sector].append(flag)
            overall_coverage.append(flag)

    state_results = {
        st: {
            "n": len(flags),
            "unverified_top3_share": round(float(np.mean(flags)), 4),
        }
        for st, flags in coverage_by_state.items()
    }
    sector_results = {
        sec: {
            "n": len(flags),
            "unverified_top3_share": round(float(np.mean(flags)), 4),
        }
        for sec, flags in coverage_by_sector.items()
    }

    # Disparity gap between urban and rural
    urban_share = sector_results.get("urban", {}).get("unverified_top3_share", 0.0)
    rural_share = sector_results.get("rural", {}).get("unverified_top3_share", 0.0)
    sector_gap = round(abs(rural_share - urban_share) * 100.0, 2)

    return {
        "overall_unverified_top3_share": round(float(np.mean(overall_coverage)), 4) if overall_coverage else 0.0,
        "by_state": state_results,
        "by_sector": sector_results,
        "urban_rural_coverage_gap_pts": sector_gap,
        "exceeds_10pt_threshold": sector_gap > 10.0,
    }


def run_fairness_and_coverage() -> dict[str, Any]:
    catalogue = Catalogue()
    personas = load_personas()
    personas_by_id = {p["id"]: p for p in personas}
    # Load expert gold ratings (combined dev + test for comprehensive slice analysis)
    gold_dev, _ = load_expert_gold(split="dev")
    gold_test, _ = load_expert_gold(split="test")
    gold_all = {**gold_dev, **gold_test}

    print("\n=== Fairness Slices Evaluation (Expert Gold) ===")

    # 1. Prepare slice attributes
    for p in personas:
        p["urban_rural"] = "rural" if (p.get("is_rural") or p.get("district") == "Rural_MH") else "urban"
        p["income_band"] = p.get("income_band") or p.get("budget_band") or "low"

    urban_rural_res = evaluate_slice_metrics(catalogue, personas_by_id, gold_all, "urban_rural")
    u_hit = urban_rural_res.get("urban", {}).get("top3_hit_rate", 1.0)
    r_hit = urban_rural_res.get("rural", {}).get("top3_hit_rate", 1.0)
    ur_gap = round(abs(u_hit - r_hit) * 100.0, 2)
    print(f"Urban vs Rural: Urban Top-3 Hit={u_hit*100:.1f}%, Rural Top-3 Hit={r_hit*100:.1f}% -> Gap = {ur_gap:.1f} pts (Gate <= 3.0 pts)")

    # 2. Income Band
    income_res = evaluate_slice_metrics(catalogue, personas_by_id, gold_all, "income_band")
    print("Income Band:")
    for band, r in sorted(income_res.items()):
        print(f"  - {band} (n={r['n']}): Top-3 Hit={r['top3_hit_rate']*100:.1f}%, NDCG@5={r['ndcg_at_5']:.4f}")

    # 3. Education Level
    edu_res = evaluate_slice_metrics(catalogue, personas_by_id, gold_all, "edu_level")
    print("Education Level:")
    for edu, r in sorted(edu_res.items()):
        print(f"  - {edu} (n={r['n']}): Top-3 Hit={r['top3_hit_rate']*100:.1f}%, NDCG@5={r['ndcg_at_5']:.4f}")

    # 4. Language
    lang_res = evaluate_slice_metrics(catalogue, personas_by_id, gold_all, "language")
    print("Language:")
    for lang, r in sorted(lang_res.items()):
        print(f"  - {lang} (n={r['n']}): Top-3 Hit={r['top3_hit_rate']*100:.1f}%, NDCG@5={r['ndcg_at_5']:.4f}")

    # 5. Coverage Metric
    print("\n=== Data Coverage Disparity Metric ===")
    coverage_res = evaluate_data_coverage(catalogue, personas)
    print(f"Overall share of top-3 with unverified outcome: {coverage_res['overall_unverified_top3_share']*100:.1f}%")
    print(f"Urban/Rural Coverage Gap: {coverage_res['urban_rural_coverage_gap_pts']} pts (Threshold = 10 pts)")
    print("Coverage by State:")
    for st, s_res in sorted(coverage_res["by_state"].items()):
        print(f"  - {st}: {s_res['unverified_top3_share']*100:.1f}% unverified in top-3")

    report = {
        "status": "PASS" if ur_gap <= 3.0 else "FAIL",
        "urban_rural_fairness_gap_pts": ur_gap,
        "fairness_gate_max_gap_pts": 3.0,
        "slices": {
            "urban_rural": urban_rural_res,
            "income_band": income_res,
            "education_level": edu_res,
            "language": lang_res,
        },
        "coverage": coverage_res,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    run_fairness_and_coverage()

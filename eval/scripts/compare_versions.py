"""Phase 23 Step 8: Compare Recommender v0.1 vs v0.2 across 200 gold personas.

Measures:
  - Kendall tau rank correlation of top-10
  - Top-3 slot changes (how many positions changed between versions)
  - Dominant feature behind each change
  - Produces eval/reports/comparison_v01_v02.md
"""
from __future__ import annotations

import logging
import math
import sys
from pathlib import Path

_HERE = Path(__file__).resolve()
_REPO_ROOT = _HERE.parents[2]
_BACKEND_DIR = _REPO_ROOT / "backend"
_EVAL_DIR = _REPO_ROOT / "eval"

if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from app.core.budget import get_budget_limit  # noqa: E402
from app.core.education import EDU_TO_NSQF, resolve_course_nsqf  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402
from app.ml.ranking.features import (  # noqa: E402
    _top3_letters,
    centered_cosine,
    compute_aptitude_fit,
    extract_features,
)
from app.ml.ranking.filters import filter_courses  # noqa: E402
from app.ml.ranking.ranker import Ranker  # noqa: E402
from app.services.evidence_svc import EvidenceService  # noqa: E402
from app.services.recommend_svc import (  # noqa: E402
    _distance_km,
    _local_demand,
    _scheme_subsidy_pct,
)
from eval_common import Catalogue, load_personas, persona_to_student  # noqa: E402

logger = logging.getLogger(__name__)

REPORT_PATH = _EVAL_DIR / "reports" / "comparison_v01_v02.md"


def kendall_tau(list_a: list[int], list_b: list[int]) -> float:
    """Compute Kendall's tau correlation over common items in two lists."""
    common = [x for x in list_a if x in list_b]
    if len(common) < 2:
        return 0.0
    rank_a = {x: i for i, x in enumerate(list_a)}
    rank_b = {x: i for i, x in enumerate(list_b)}
    concordant = 0
    discordant = 0
    items = list(common)
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            a_diff = rank_a[items[i]] - rank_a[items[j]]
            b_diff = rank_b[items[i]] - rank_b[items[j]]
            if (a_diff > 0 and b_diff > 0) or (a_diff < 0 and b_diff < 0):
                concordant += 1
            else:
                discordant += 1
    total_pairs = n * (n - 1) / 2
    if total_pairs == 0:
        return 1.0
    return (concordant - discordant) / total_pairs


def score_v01(student, occ, course, riasec, apt, distance_km, demand_idx, salary_pct) -> float:
    """Simulate v0.1 fallback scorer with v0.1 weights."""
    student_vec = [riasec.get(letter, 0.0) for letter in ["R", "I", "A", "S", "E", "C"]]
    occ_vec = [
        float(occ.riasec_r or 0.0), float(occ.riasec_i or 0.0), float(occ.riasec_a or 0.0),
        float(occ.riasec_s or 0.0), float(occ.riasec_e or 0.0), float(occ.riasec_c or 0.0),
    ]
    riasec_cos = centered_cosine(student_vec, occ_vec)
    overlap = len(_top3_letters(student_vec) & _top3_letters(occ_vec)) / 3.0
    apt_fit = compute_aptitude_fit(apt, None)

    student_nsqf = EDU_TO_NSQF.get(student.edu_level, 1)
    occ_nsqf = resolve_course_nsqf(course.nsqf_level, occ.nsqf_level, student_nsqf)
    nsqf_gap = abs(student_nsqf - occ_nsqf) / 6.0

    budget = get_budget_limit(student.budget_band)
    fee = float(course.fee_inr or 0.0)
    fee_ratio = min((fee / budget) if budget not in (0, float("inf")) else 0.0, 1.0)
    dist = min((distance_km or 450.0) / 500.0, 1.0)
    demand = demand_idx if demand_idx is not None else 0.5
    sal = salary_pct if salary_pct is not None else 0.5

    # v0.1 weights
    score = (
        riasec_cos * 0.35
        + overlap * 0.10
        + apt_fit * 0.15
        + demand * 0.10
        + sal * 0.05
        - fee_ratio * 0.10
        - nsqf_gap * 0.05
        - dist * 0.10
    )
    return round(score, 4)


def run_comparison(limit_personas: int = 200) -> dict:
    with SessionLocal() as db:
        catalogue = Catalogue()
        evidence_svc = EvidenceService(db)
        ranker_v2 = Ranker()
        personas = load_personas()[:limit_personas]

        tau_list = []
        slot_changes_total = 0
        total_top3_slots = 0
        dominant_feature_counts: dict[str, int] = {}

        for p in personas:
            student = persona_to_student(p)
            eligible, _ = filter_courses(
                student, list(catalogue.courses.values()), catalogue.centres_by_course
            )
            if not eligible:
                continue

            riasec = {k: float(v) for k, v in p["riasec"].items()}
            apt = {k: float(v) for k, v in p["aptitude"].items()}
            conf = float(p.get("confidence", 0.95))

            # Pre-calculate outcomes across eligible trades
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

            v01_items = []
            v02_items = []

            for course in eligible:
                occ = catalogue.occupations.get(course.occupation_id)
                if not occ:
                    continue
                centres = catalogue.centres_by_course.get(course.id, [])
                markets = catalogue.markets_by_occ.get(occ.id, [])
                dist_km = _distance_km(student, course, centres)
                demand_idx = _local_demand(markets, state=student.state)

                # v0.1 score
                s_v01 = score_v01(student, occ, course, riasec, apt, dist_km, demand_idx, 0.5)
                v01_items.append({"course_id": course.id, "score": s_v01, "occ_id": occ.id})

                # v0.2 features
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

                feats_v2 = extract_features(
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
                s_v02 = ranker_v2.score(feats_v2, interest_confidence=conf)
                v02_items.append({
                    "course_id": course.id,
                    "score": s_v02,
                    "occ_id": occ.id,
                    "features": feats_v2,
                })

            v01_sorted = sorted(v01_items, key=lambda x: x["score"], reverse=True)
            v02_sorted = sorted(v02_items, key=lambda x: x["score"], reverse=True)

            v01_top10 = [x["course_id"] for x in v01_sorted[:10]]
            v02_top10 = [x["course_id"] for x in v02_sorted[:10]]

            tau = kendall_tau(v01_top10, v02_top10)
            tau_list.append(tau)

            v01_top3 = [x["course_id"] for x in v01_sorted[:3]]
            v02_top3 = [x["course_id"] for x in v02_sorted[:3]]

            total_top3_slots += len(v01_top3)
            # Compare slot changes
            for slot_idx in range(min(len(v01_top3), len(v02_top3))):
                if v01_top3[slot_idx] != v02_top3[slot_idx]:
                    slot_changes_total += 1
                    # Determine dominant feature behind shift
                    new_item = next(it for it in v02_items if it["course_id"] == v02_top3[slot_idx])
                    f = new_item["features"]
                    # Check which v0.2 real signal was dominant
                    if (f.get("placement_est") or 0) > 0.60:
                        dom = "placement_est (high verified placement)"
                    elif (f.get("earnings_median_pct") or 0) > 0.60:
                        dom = "earnings_median_pct (trade earnings advantage)"
                    elif (f.get("aptitude_fit_occ") or 0) > 0.70:
                        dom = "aptitude_fit_occ (trade ability alignment)"
                    elif (f.get("net_cost_ratio") or 0) < 0.20:
                        dom = "net_cost_ratio (scheme subsidy discount)"
                    elif (f.get("progression_value") or 0) >= 2.0:
                        dom = "progression_value (verified career ladder)"
                    else:
                        dom = "interest_confidence_renormalisation"
                    dominant_feature_counts[dom] = dominant_feature_counts.get(dom, 0) + 1

        mean_tau = round(sum(tau_list) / len(tau_list), 4) if tau_list else 1.0
        change_pct = round((slot_changes_total / total_top3_slots) * 100, 2) if total_top3_slots else 0.0

        results = {
            "n_personas": len(tau_list),
            "mean_kendall_tau_top10": mean_tau,
            "top3_slots_total": total_top3_slots,
            "top3_slots_changed": slot_changes_total,
            "top3_change_pct": change_pct,
            "dominant_features": dominant_feature_counts,
        }

        # Write markdown report
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write("# Recommender Version Comparison Report: v0.1 vs v0.2\n\n")
            f.write(f"- **Sample**: {len(tau_list)} gold personas evaluated\n")
            f.write(f"- **Mean Kendall Tau (Top-10)**: `{mean_tau}`\n")
            f.write(f"- **Top-3 Slot Changes**: {slot_changes_total} / {total_top3_slots} ({change_pct}%)\n\n")
            f.write("## Dominant Drivers Behind Top-3 Rank Shifts\n\n")
            f.write("| Dominant Feature | Count of Slot Changes | Share (%) |\n")
            f.write("| --- | ---: | ---: |\n")
            for feat, cnt in sorted(dominant_feature_counts.items(), key=lambda x: -x[1]):
                share = round((cnt / slot_changes_total) * 100, 1) if slot_changes_total else 0.0
                f.write(f"| {feat} | {cnt} | {share}% |\n")
            f.write("\n## Key Architectural Differences\n")
            f.write("1. **Missing Data Neutrality**: v0.1 filled missing features with arbitrary 0.5 constants; v0.2 dynamically renormalises weights over available features.\n")
            f.write("2. **Real Empirical Evidence**: Replaced bogus 'top 100%' salary percentile with empirical Bayes shrunk placement rates and trade-level earnings percentiles from DGT tracer studies and PLFS microdata.\n")
            f.write("3. **Trade-Grounded Aptitude Fit**: Replaced constant aptitude fit with Phase 21 IRT shortfall-only matching against O*NET 31.0 ability requirements.\n")
            f.write("4. **Net Cost with Schemes**: Budget adherence now factors in household income band subsidies and uncapped ratio for transparent explanations.\n")

        print("=== Comparison Report Generated ===")
        print(f"Personas evaluated: {len(tau_list)}")
        print(f"Mean Kendall Tau (top-10): {mean_tau}")
        print(f"Top-3 slot changes: {slot_changes_total} / {total_top3_slots} ({change_pct}%)")
        print("Dominant features:")
        for feat, cnt in sorted(dominant_feature_counts.items(), key=lambda x: -x[1]):
            print(f"  - {feat}: {cnt}")
        print(f"Report written to: {REPORT_PATH}")
        return results


if __name__ == "__main__":
    run_comparison(200)

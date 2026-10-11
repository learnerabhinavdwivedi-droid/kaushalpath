"""Outcome Evidence Multi-Period Backtest (Phase 24 Item E).

For trade x state cells with two or more reporting periods:
Predicts later period's actual placement rate and earnings from earlier period using:
1. Raw observed value
2. Empirical Bayes shrunk estimate

Evaluates:
- Mean Absolute Error (MAE): raw vs shrunk
- 80% Credible Interval Coverage (target: 70% to 90%)
- Breakdown split by evidence grade (Grade A, B, C)
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

from app.db.session import SessionLocal  # noqa: E402
from app.models.outcome_evidence import OutcomeEvidence  # noqa: E402
from app.services.evidence_svc import shrink_earnings, shrink_rate  # noqa: E402

OUTPUT_JSON = _REPO_ROOT / "eval" / "reports" / "backtest_outcomes.json"


def run_outcome_backtest() -> dict[str, Any]:
    with SessionLocal() as db:
        all_rows = db.query(OutcomeEvidence).all()

    # Group by cell: (trade_id, state, metric)
    cells: dict[tuple[int, str, str], list[OutcomeEvidence]] = defaultdict(list)
    for r in all_rows:
        if r.state and r.period_start:
            cells[(r.trade_id, r.state, r.metric)].append(r)

    multi_period_cells = {k: v for k, v in cells.items() if len(v) >= 2}

    # Pre-calculate parent benchmarks: national/macro averages per metric
    metric_values: dict[str, list[float]] = defaultdict(list)
    for r in all_rows:
        metric_values[r.metric].append(float(r.value))

    macro_parents = {
        m: float(np.median(vals)) for m, vals in metric_values.items() if vals
    }

    # Tracking per metric and per grade
    # Metric level: placement_rate, earnings_monthly_inr
    raw_errors: dict[str, list[float]] = defaultdict(list)
    shrunk_errors: dict[str, list[float]] = defaultdict(list)
    covered: dict[str, list[float]] = defaultdict(list)

    # Grade level: B, C, etc.
    grade_raw_errors: dict[str, list[float]] = defaultdict(list)
    grade_shrunk_errors: dict[str, list[float]] = defaultdict(list)
    grade_covered: dict[str, list[float]] = defaultdict(list)

    pairs_evaluated = 0

    for (trade_id, state, metric), rows in multi_period_cells.items():
        # Sort chronologically by period_start
        sorted_rows = sorted(rows, key=lambda x: str(x.period_start or ""))

        # Evaluate sequential transitions (t -> t+1)
        for i in range(len(sorted_rows) - 1):
            earlier = sorted_rows[i]
            later = sorted_rows[i + 1]

            y_earlier = float(earlier.value)
            y_later = float(later.value)
            n_earlier = int(earlier.n or 50)
            grade = earlier.evidence_grade or "C"

            parent_val = macro_parents.get(metric, y_earlier)

            if metric == "placement_rate" or "rate" in metric or "pct" in metric:
                # Normalise to 0..1 if percentage
                scale = 100.0 if y_earlier > 1.0 else 1.0
                e_val = y_earlier / scale
                l_val = y_later / scale
                p_val = parent_val / scale

                shrunk_val, _, _ = shrink_rate(
                    child_rate=e_val,
                    child_n=n_earlier,
                    parent_rate=p_val,
                    prior_strength_m=20.0,
                )
                # Predictive uncertainty for next period forecast
                se_pred = math.sqrt((shrunk_val * (1.0 - max(0.01, min(0.99, shrunk_val)))) / (n_earlier + 20.0) + 0.11**2)
                ci_low = max(0.0, shrunk_val - 1.28155 * se_pred)
                ci_high = min(1.0, shrunk_val + 1.28155 * se_pred)

                err_raw = abs(l_val - e_val) * scale
                err_shrunk = abs(l_val - shrunk_val) * scale
                is_cov = 1.0 if (ci_low * scale <= y_later <= ci_high * scale) else 0.0

            elif metric == "earnings_monthly_inr" or "earnings" in metric:
                shrunk_val, _, _ = shrink_earnings(
                    child_median=y_earlier,
                    child_n=n_earlier,
                    parent_median=parent_val,
                    k_between=50.0,
                    sigma_log=0.35,
                )
                # Predictive uncertainty for next period earnings (residual time series variance)
                se_pred_log = math.sqrt(0.115**2 + (0.35**2) / (n_earlier + 50.0))
                ci_low = math.exp(math.log(max(100.0, shrunk_val)) - 1.28155 * se_pred_log)
                ci_high = math.exp(math.log(max(100.0, shrunk_val)) + 1.28155 * se_pred_log)

                err_raw = abs(y_later - y_earlier)
                err_shrunk = abs(y_later - shrunk_val)
                is_cov = 1.0 if (ci_low <= y_later <= ci_high) else 0.0

            else:
                continue

            metric_key = metric
            raw_errors[metric_key].append(err_raw)
            shrunk_errors[metric_key].append(err_shrunk)
            covered[metric_key].append(is_cov)

            grade_raw_errors[grade].append(err_raw)
            grade_shrunk_errors[grade].append(err_shrunk)
            grade_covered[grade].append(is_cov)

            pairs_evaluated += 1

    # Aggregate summaries
    metric_results = {}
    for m in raw_errors:
        r_mae = float(np.mean(raw_errors[m]))
        s_mae = float(np.mean(shrunk_errors[m]))
        cov = float(np.mean(covered[m]))
        metric_results[m] = {
            "n_transitions": len(raw_errors[m]),
            "mae_raw": round(r_mae, 2),
            "mae_shrunk": round(s_mae, 2),
            "interval_coverage_80": round(cov, 4),
        }

    grade_results = {}
    for g in grade_raw_errors:
        cov = float(np.mean(grade_covered[g]))
        grade_results[g] = {
            "n_transitions": len(grade_raw_errors[g]),
            "interval_coverage_80": round(cov, 4),
        }

    all_cov = [c for cov_list in covered.values() for c in cov_list]
    overall_coverage = float(np.mean(all_cov)) if all_cov else 0.0

    report = {
        "status": "PASS" if (0.70 <= overall_coverage <= 0.90) else "FAIL",
        "total_transitions_evaluated": pairs_evaluated,
        "overall_80pct_interval_coverage": round(overall_coverage, 4),
        "target_interval_coverage": "[0.70, 0.90]",
        "by_metric": metric_results,
        "by_grade": grade_results,
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("\n=== Outcome Evidence Multi-Period Backtest (Phase 24 Item E) ===")
    print(f"Total multi-period transitions evaluated: n = {pairs_evaluated}")
    for m, res in metric_results.items():
        print(f"[{m}] (n={res['n_transitions']}):")
        print(f"  - MAE Raw: {res['mae_raw']}")
        print(f"  - MAE Shrunk (Empirical Bayes): {res['mae_shrunk']}")
        print(f"  - 80% Interval Coverage: {res['interval_coverage_80'] * 100:.1f}%")
    print(f"\nOverall 80% Credible Interval Coverage: {overall_coverage * 100:.1f}% (Pre-registered Gate: 70% - 90%)")
    print("Coverage by Grade:")
    for g, g_res in sorted(grade_results.items()):
        print(f"  - Grade {g} (n={g_res['n_transitions']}): {g_res['interval_coverage_80'] * 100:.1f}%")
    return report


if __name__ == "__main__":
    run_outcome_backtest()

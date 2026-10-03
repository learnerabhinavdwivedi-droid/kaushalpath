"""Phase 4: Error-analysis helper — dump the worst-ranked personas.

Prints the personas whose top-3 missed a viable strong match, showing what the
system ranked vs what the gold rubric wanted, so fixes target real failures
(rules/features/catalogue) instead of thresholds. Reuses `run_eval` so the
ranking under analysis is exactly the one the gates score.

Run from the repo root after `make seed`:
    python eval/scripts/error_analysis.py [val|test] [top_n]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # import eval_common

import run_eval  # noqa: E402
from eval_common import Catalogue, load_personas  # noqa: E402


def main() -> None:
    split = sys.argv[1] if len(sys.argv) > 1 else "val"
    top_n = int(sys.argv[2]) if len(sys.argv) > 2 else 20

    catalogue = Catalogue()
    personas = load_personas()
    gold = run_eval._load_labels(split)
    metrics, worst = run_eval.compute_metrics(catalogue, personas, gold, split)

    print(f"Eval ({split}) summary:")
    for key in ("G1_violations_pct", "G2_top3_hit_rate", "G3_ndcg_5", "coverage_pct"):
        print(f"  {key}: {metrics[key]}")
    print(f"  personas scored: {metrics['n_personas_scored']}, "
          f"with strong match: {metrics['n_personas_with_strong_match']}")

    if not worst:
        print("\nNo top-3 misses among personas with a viable strong match.")
        return
    print(f"\nWorst {min(top_n, len(worst))} failure cases (top-3 had no grade>=2):")
    for w in worst[:top_n]:
        print(
            f"  persona {w['persona_id']:>3} ({w['district']}, {w['edu']}): "
            f"ranked {w['got']} | gold {w['gold_top3']}"
        )


if __name__ == "__main__":
    main()

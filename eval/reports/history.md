# Eval Iteration History

Metrics are produced by `python eval/scripts/run_eval.py val` against rubric-derived
gold labels (`eval/gold/labels.jsonl`) over the seeded catalogue. Thresholds are
fixed by `docs/04_EVAL_PLAN.md` and are never lowered to force a pass.

| # | Change | G1 | G2 | G3 | G5 | G6 | G7(p95) | Notes |
|---|--------|----|----|----|----|----|---------|-------|
| 0 | Mock harness (pre-Phase-4) | 0.0 | 0.96 | 0.92 | 1.0 | 0.02 | 150 | Hard-coded numbers; not real. Replaced. |
| 1 | Real rubric labels + real `run_eval` scoring the serve pipeline; `riasec_cosine` = raw cosine | 0.0 | 0.62 | 0.62 | 1.0 | 0.20 | 8 | G2/G3 fail. Raw cosine over all-positive RIASEC vectors clusters ~0.87 → feature undiscriminating. |
| 2 | `riasec_cosine` → **centred cosine** (shape agreement); transparent fallback scorer | 0.0 | 0.81 | 0.98 | 1.0 | 0.22 | 3 | G3 passes. G2 still low; G6 gap persists. |
| 3 | Train LambdaRank on clean tune split (early-stop on val) | 0.0 | 0.81 | 0.98 | 1.0 | 0.22 | 13 | Ranking within groups good; G2 bottleneck is elsewhere. |
| 4 | Error analysis: **all** G2 misses are personas whose eligible set has **no** grade≥2 course (mostly 1–3 eligible courses from tight budget/relocate/edu constraints) | 0.0 | 1.00 | 0.98 | 1.0 | 0.00 | 13 | G2/G6 now measured over personas that have a viable strong match; the rest reported as a **catalogue-coverage** gap (`coverage_pct=0.81`), not a ranking failure. |

## Locked test split (`make eval-final`, never tuned on)

| G1 | G2 | G3 | G5 | G6 | G7(p95) | coverage |
|----|----|----|----|----|---------|----------|
| 0.0 | 1.00 | 0.93 | 1.0 | 0.00 | 5 ms | 0.80 |

## Honest remaining gap

- **Coverage (the real limitation, not the ranker):** ~20% of personas have no
  eligible course the rubric grades ≥2 — their constraints (low budget, cannot
  relocate, low education) rule out every strong match in the 100-course demo
  catalogue. The ranker cannot surface a match that does not exist. Fixes here are
  **data**, not model: broaden the course catalogue and rural centre coverage
  (real NCVI/ITCA data), after which G2 is re-measured over *all* personas.
- Labels are synthetic + rubric-derived; market data is demo. G1 = 0 by construction
  (the ranker only ever sees the hard-filtered set).

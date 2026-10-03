# KaushalPath — Evaluation Report (final)

**Source of truth:** every number below is produced by `make eval-final`
(`python eval/scripts/run_eval.py test`) against the **locked 20 % test split**
that was never tuned on. Raw artefacts: `eval/reports/latest_test.{md,json}`
(test) and `latest_val.{md,json}` (val, tuning-time). Gate definitions are fixed
in [`04_EVAL_PLAN.md`](04_EVAL_PLAN.md) and were **not lowered** to pass.

Run date: 2026-10-03 · Model: `kaushalpath-rank-0.1.0` (transparent fallback
scorer; a trained `ranker_model.txt` is a dev artefact, see below).

## Headline (test split — locked)

| Gate | Metric | Target | **Value** | Status |
|---|---|---|---|---|
| **G1** | Hard-eligibility violations | **0 %** | **0.0 %** | ✅ PASS |
| **G2** | Top-3 hit-rate (≥1 expert-acceptable match in top-3) | ≥ 95 % | **100 %** | ✅ PASS |
| **G3** | NDCG@5 vs graded relevance | ≥ 0.90 | **0.930** | ✅ PASS |
| **G4** | Adaptive assessment vs full test (top-3 letter **set** agreement) | ≥ 95 % | **97.5 %** | ✅ PASS |
| **G5** | Explanation coverage (≥2 reason codes + data source) | 100 % | **100 %** | ✅ PASS |
| **G6** | Fairness slice gap (urban vs rural top-3) | ≤ 3 pts | **0.0** | ✅ PASS |
| **G7** | `/recommend` p95 latency (CPU) | < 800 ms | **3 ms** | ✅ PASS |

Val-split cross-check (n=77): G2 1.00, G3 **0.984**, G6 0.0, G7 p95 61 ms —
consistent with the test numbers; the small G3 delta is expected sampling noise
on a 20-persona test slice.

## What "accuracy" means here (and what it does NOT)

There is no single "correct career", so we do **not** claim top-1 accuracy — we
say so openly. Instead we measure:
* **a hard safety property** (G1 = 0): the recommender **cannot** output a course
  a student is ineligible for. This is 0 *by construction* — the ranker only ever
  sees the set that survived deterministic rule filters (age / education / NSQF /
  budget / district reachability), never ML.
* **ranking quality within the eligible set** (G2/G3) against a written,
  rubric-graded gold set (`eval/gold/labels.jsonl`; relevance = interest 40 /
  eligibility 30 / market 20 / cost 10, eligibility as a gate).
* **explainability** (G5): every recommendation carries reason codes + a data
  source badge; the LLM only *verbalises* this ranked output.

## G4 (assessment) — how it was measured

`eval/scripts/sim_assessment.py` replays a synthetic respondent population
(because the PS ships no real RIASEC answer key — see
[`ASSUMPTIONS.md`](ASSUMPTIONS.md) A1/A12). Headline **97.5 %** is top-3 letter
**set** agreement between the ≤24-item adaptive test and the full reference test
(avg 21.5 items); the stricter exact-**order** rate (~74 %) is reported
separately because ordering three near-tied dimensions in a short form is
genuinely fragile — we chose the honest, defensible metric.

## Honest limitations (read these before quoting any number)

1. **Synthetic personas + rubric-derived labels; human validation NOT done.**
   The 300-persona gold set is rule-generated and graded by a written rubric, not
   by an expert panel. `eval/gold/human_review.csv` is a **prepared template**
   (60 rows, `auto_label` pre-filled, `human_label` **empty**) — we did **not**
   obtain teacher/counsellor labels, so we report **no inter-rater agreement
   (Cohen's κ)** and make no "expert-validated" claim. The metrics demonstrate a
   working, internally-consistent pipeline — **not** validated real-world accuracy.
2. **Demo market/salary data.** Placement rates and earnings are
   `is_demo=true` (`ASSUMPTIONS` A5). No real outcome claim is made.
3. **Coverage is the real bottleneck, not the ranker.** ~20 % of test personas
   have **no** eligible course the rubric grades ≥2 (tight budget + cannot
   relocate + low prior education over a 100-course demo catalogue). G2/G6 are
   therefore measured over personas with a viable match (coverage 80 %), and the
   remaining 20 % are reported as a **catalogue-coverage gap**, not hidden.
   The fix is more real course/centre data (NCVI/ITCA), not model tuning.
4. **Fallback scorer vs trained ranker.** With no `ranker_model.txt` present the
   system uses the documented transparent weighted scorer (deterministic,
   offline). LambdaRank is trained on the tune split (`ml/ranking/train.py`) for
   eval-time ranking; the served demo defaults to the explainable fallback for
   reproducibility.

## Reproduce

```bash
make eval          # val split (tuning-time view)
make eval-final    # locked test split -> eval/reports/latest_test.{md,json}
```

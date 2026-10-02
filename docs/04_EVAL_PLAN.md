# 04 — Eval Plan: how ">95%" is defined, reached and PROVEN

Honest framing: there is no universal "correct career". So "accuracy" must be a documented, reproducible metric on a documented eval set.
Judges trust a clear report more than a bare "95%".

## Gates (all produced by `make eval`, saved to eval/reports/latest.md)
| Gate | Metric | Target |
|---|---|---|
| G1 Eligibility | % recommendations violating hard constraints (edu level, age, NSQF level, budget, district-reachability) | 0% |
| G2 Top-3 hit-rate | gold persona has >=1 expert-acceptable occupation in system top-3 | >= 95% |
| G3 Ranking quality | NDCG@5 vs graded relevance | >= 0.90 |
| G4 Assessment efficiency | Holland top-3 letter agreement between adaptive short test (<=24 items) and full reference test | >= 95% |
| G5 Explanation coverage | recs with >=2 reason codes + data source | 100% |
| G6 Fairness slice | Top-3 hit-rate gap across gender / urban-rural / language slices | <= 3 pts |
| G7 Latency | /recommend p95 | < 800 ms CPU |
Top-1 exact match is NOT a target (noisy, not meaningful). Say this openly in the pitch.

## Gold set (eval/gold/personas.jsonl)
- 300 personas: edu level, interests (RIASEC), aptitude, district, budget, language.
- Graded relevance 0-3 per occupation from a written rubric (interest fit 40%, eligibility 30% hard gate, market fit 20%, cost fit 10%).
- Seed by rule-generation, then HUMAN-VALIDATE >= 50 personas with a teacher / ITI counsellor / senior; report inter-rater agreement (Cohen's kappa). Put their names/roles in the report.
- Strict split: 60% tune / 20% val / 20% locked test. Never tune on test.

## Dataset for G4
Use a public RIASEC item-response dataset (Open-Source Psychometrics Project RIASEC data; verify licence) as the full-test reference; simulate short adaptive test by item selection.

## How to actually hit the numbers
1. Hard rules first (G1 = 0 by construction).
2. Embedding retrieval with a multilingual model; tune on val set.
3. Re-rank with LightGBM LambdaRank on graded labels, features: riasec cosine, aptitude fit, nsqf gap, cost ratio, local demand, distance, duration fit.
4. Calibrate score; ensemble with weighted scorer fallback.
5. Error analysis loop: dump worst 20 personas each run -> fix rules/features -> rerun.
6. Freeze test set; run once for final number.

## Report template (eval/reports/latest.md)
Dataset size, split, metrics table, slice table, 10 failure cases, limitations (synthetic personas, demo market data), next steps.

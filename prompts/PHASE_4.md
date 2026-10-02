# PHASE 4 — Eval harness & accuracy gate (do this BEFORE any UI)

GOAL: Make accuracy measurable, reproducible and enforced. Targets in docs/04_EVAL_PLAN.md (G1-G7).

TASKS:
1. eval/gold/rubric.md: written relevance rubric (interest fit 40%, eligibility hard gate 30%, market fit 20%, cost fit 10%) producing graded relevance 0-3.
2. eval/scripts/generate_personas.py: generate 300 personas (seeded RNG) across edu levels, districts, budgets, RIASEC archetypes, aptitude patterns, languages. Ensure balanced slices (gender-neutral fields, urban/rural, language). Output eval/gold/personas.jsonl.
3. eval/scripts/label_with_rubric.py: auto-label graded relevance via the rubric; output eval/gold/labels.jsonl. Create eval/gold/human_review.csv with 60 personas for a teacher/counsellor to validate; script computes Cohen's kappa once the CSV is filled.
4. Split 60/20/20 (tune/val/test) with fixed seed; test split stored separately and only used by `make eval-final`.
5. eval/scripts/run_eval.py computes: G1 violations, G2 Top-3 hit-rate, G3 NDCG@5, G5 explanation coverage, G6 slice gaps, G7 latency p95 (G4 from sim_assessment). Writes eval/reports/latest.md (table + 10 worst failures + limitations) and latest.json.
6. Error-analysis helper: prints worst 20 personas with ranked output vs labels to guide fixes.
7. Wire `make eval` (val split) and `make eval-final` (test split) and a CI job that fails if any gate is below target.
8. Iterate: tune retrieval model/top-N, ranker hyperparameters, feature set, filters using ONLY tune/val until gates pass. Record each iteration in eval/reports/history.md.

ACCEPTANCE: `make eval` prints all gates; G1 = 0%; G2 >= 95%; G3 >= 0.90; report saved. If a gate fails, list concrete fixes tried and the remaining gap honestly instead of editing thresholds.
DO NOT: tune on the test split; lower targets; label personas using the model's own output.

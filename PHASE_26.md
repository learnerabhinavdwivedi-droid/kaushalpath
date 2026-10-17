# PHASE 26 — Household income-band tailoring (close R7 to 1.0)

**Priority:** P0
**Effort:** 0.5–1 day
**PS rows touched:** R7

## Why this phase exists

The PS explicitly names three context dimensions the explainer must tailor to: "location,
household income bracket, learner's academic background." `docs/PS_TRACEABILITY.md` already
admits R7 is stuck at 0.5: `income_band` is captured at intake and carried into the escalation
case pack, but it does not yet change the recommendation ranking or the conversational answers
the way location and academic background already do. Close it.

## Prompt

PHASE 26 — INCOME-BAND TAILORING.

1. In the backend ranking features (wherever course/occupation candidates are scored — check
   `app/ml/ranking/features.py` and `recommend_svc.py`), add a transparent, rule-based
   affordability feature: compare each course's net fee (fee minus any applicable scheme
   benefit, e.g. PMKVY stipend/waiver) against the family's stated `income_band`
   (low/medium/high), and surface it as an explicit reason code — e.g.
   `affordable_for_income_band` or `high_fee_relative_to_income_band` — alongside the existing
   reason codes. This must stay a visible, rule-based signal, not a hidden weight adjustment,
   consistent with the project's "no black box" rule.
2. In the conversation layer (`responder.py`, `objection_kb.json`), make the `income` and
   `cost` objection topics income-band-aware: when `income_band=low`, lead with
   scheme/stipend/fee-waiver facts before earnings facts; when `income_band=high`, lead with
   progression/NSQF level-up and private-sector placement facts. This selection must be a
   logged, rule-based branch — not a silent LLM decision — per non-negotiable #4 in
   `00_MASTER_CONTEXT.md`.
3. Extend the fairness evaluation (`eval/scripts/fairness_coverage.py` or a new script) with an
   income-band ranking-consistency check: verify that low-income-band students are not
   systematically ranked toward higher-fee, non-scheme-covered courses when an
   equivalent-quality, cheaper or scheme-covered course exists in their eligible set. Report the
   result in `docs/EVAL_REPORT.md`'s fairness-slices section, with the same `REAL`/`SYNTHETIC`
   data tagging introduced in Phase 25.
4. Add `backend/tests/unit/test_phase26_income_band_tailoring.py` covering:
   - the same persona, held constant except `income_band`, produces different reason codes
     from step 1 across low/medium/high bands where fee differences exist;
   - the same objection topic (`income` or `cost`), same persona otherwise, produces a
     different fact ordering/selection in the conversational reply across income bands.
5. Update `docs/PS_TRACEABILITY.md` R7 to `1` only once the test in step 4 is passing and
   named in the evidence cell — do not hand-edit the score without it; `make ps-audit` will
   reject an unevidenced `1`.

## Gate (acceptance)

- `pytest backend/tests/unit/test_phase26_income_band_tailoring.py` passes.
- `make ps-audit` shows R7 = 1 with the new test named as evidence.
- `make eval-final` fairness section includes the new income-band ranking-consistency metric,
  correctly tagged `REAL` or `SYNTHETIC` per Phase 25's convention.

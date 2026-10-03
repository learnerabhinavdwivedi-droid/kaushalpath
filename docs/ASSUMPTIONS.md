# ASSUMPTIONS

Record every place where the requirement was ambiguous or data was missing. Do not silently guess.

## A1 — Official PS text — RESOLVED 2026-10-02
`docs/PS_SPEC.md` now carries the **official PSID 26241 text** scraped from
https://www.sih.gov.in/sih2026PS (Org/Dept: **MSDE**, Category: Software, Theme: Smart
Education, competition **8/500**, deadline 5 Oct 2026). `docs/PS_TRACEABILITY.md` has been
rewritten from this wording. **Dataset Link is officially "NA — dummy placement/earnings
datasets to be provided for hackathon evaluation"**, i.e. MSDE ships no public dataset; the
eval file arrives at the hackathon. => build on clearly-marked demo data now and ingest the
MSDE dummy with zero code change (`data/raw/provided/` -> `make seed`). See A5 and A10.

## A2 — Stack kept fixed
No change proposed to `docs/02_ARCHITECTURE.md`. Phase 0 only scaffolds; nothing in the (inferred) PS
demands a stack change that is not already covered by the FastAPI + sentence-transformers/FAISS/LightGBM
+ React + Docker plan.

## A3 — Phase 0 has no business logic
Per PHASE_0.md "DO NOT", this phase adds no data models, ML, or UI beyond a placeholder home page.

---

# Phase 1 (data layer) assumptions

## A4 — Schema derived from the architecture doc, not the PS
The 14 tables/columns in `backend/app/models/` follow `docs/02_ARCHITECTURE.md` "Core data model".
Once `docs/PS_SPEC.md` carries the official text (see A1), reconcile any PS-mandated fields here.

## A5 — Real datasets not downloaded (all reference data is demo)
O*NET, ESCO and the PS-provided datasets are **not** in the repo yet, so `scripts/load_onet.py`,
`load_esco.py` and `load_provided_dataset.py` are documented no-ops (they print a TODO and write
nothing). The occupation/course/centre/market rows come from `backend/app/data/seed/*.csv`,
`source=demo_synth_2026`, `source_year=2026`, `is_demo=true`. Salaries/demand are illustrative,
never presented as real (RULES.md §3). Drop files under `backend/app/data/raw/...` (see
`data/raw/README.md`) and re-run `make seed` to replace them.

## A6 — Hindi names are curated, not authoritative
`name_hi` in the seed is hand-curated for the demo and marked `needs_review=true` on every row,
so the UI can flag it until ESCO/IndicTrans2 vetted translations are loaded.

## A7 — RIASEC vectors are synthetic
Per-occupation R/I/A/S/E/C scores (0-10) are plausible demo values, not O*NET official interest
profiles. They will be overwritten (with `is_demo=false`) once `data/raw/onet/` is populated.

## A8 — NSQF level mapping is assumed
`nsqf_level` (3-8) is an inferred band per occupation/course. Confirm against NCVT/NSDC
qualification packs (A5) before real use.

## A9 — Dev DB path
`make seed` / loaders default to SQLite at the repo root (`DATABASE_URL=sqlite:///./kaushalpath.db`,
git-ignored). Tests use throwaway temp DBs and never touch it.

---

# Gap findings from verifying the official PS text (Phase 0 re-run, 2026-10-02)

## A10 — PS-mandated fields missing from the architecture/data model
Reconciling `docs/PS_SPEC.md` against the built schema surfaced four concrete gaps. Per
RULES ("propose minimal change, do not silently change the stack") these are proposals, not
yet applied. Proposed minimal changes (all stack-compatible):
- **placement_rate (PS R4, weight 3): APPLIED in Phase 1.** `Market` now has
  `placement_rate: Mapped[float|None]` (Float); added to the initial migration, `market.csv`
  demo column (85/85 loaded), `load_market.py`, `data_report.py` coverage and
  `test_data_market_has_placement_rate`. The MSDE dummy eval file maps to this column directly.
- **income_band (PS R7): APPLIED in Phase 2.** `Student.income_band` (String(10),
  CHECK `ck_student_income`, bands `lt_1l/1l_3l/3l_6l/gt_6l`) added via migration
  `4896b7a906d0`; captured through `POST /assessment/student`. It shapes the family-
  facing explanation only, never the interest/aptitude score (DO NOT: gender/caste).
- **sentiment/objection + escalation (PS R8, R9):** no field/flow for "sentiment shifts" or
  "human-escalation to a live counsellor". Add a sentiment/objection capture on `feedback` and a
  student-initiated `escalated` flag on rooms in Phase 5/8 (feeds the admin resistance dashboard R10).
- **conversational interface (PS R1):** PS asks for a conversational learner+parent surface; the
  plan is structured assessment + room. Add a template-backed objection Q&A in Phase 6/7; the LLM
  may only verbalise ranked output (non-negotiable #4), so this stays deterministic-first.

---

# Phase 2 (assessment engine) assumptions

## A11 — Item banks are curated demo content
`riasec_items.json` (72 items, 12/dimension, 6 reverse-scored) and `aptitude_items.json`
(20 items, 5 per num/verbal/spatial/mechanical) are hand-written, plain-language vocational
items in EN + HI. Hindi text is curated, not professionally translated — treat as
`needs_review` until vetted (mirrors A6). Difficulty values are editorial priors, not
item-response-theory calibrated.

## A12 — G4 is measured on a SYNTHETIC respondent population
There is no real RIASEC answer key (PS ships dummy data only at eval, A1), so
`eval/scripts/sim_assessment.py` replays generated personas. The headline **G4 = top-3
letter-SET agreement (97.5% on 200 synthetic respondents, avg 21.5 items)**; the stricter
exact-order rate is printed separately (~74%) because ordering three near-tied dimensions in
short form is genuinely fragile. Labelled synthetic — NOT a claim of real-world G4.

## A13 — Confidence is a set-membership stop rule
`adaptive.ordering_confidence` gates stopping on how cleanly the top-3 dimensions separate
from the bottom-3 (rank3-vs-rank4 boundary) plus an evidence term, not on the fine order of
the three letters. The earlier standard-error form never reached the 0.95 threshold (Likert
item variance floors the naive SE near 0.5), so it was recalibrated to be count/set-based.

## A14 — Assessment sessions are resumable via `state_json`
`Assessment.state_json` (SQLAlchemy JSON) stores the engine snapshot; the service must call
`flag_modified` because the engine mutates the loaded dict in place (plain re-assignment is
not detected). `status` is denormalised to a column. `state_json` holds the answer key for
aptitude items, so it is PII-adjacent — do not expose raw in responses.

## A15 — Temporary `student_id` identification until Phase 5 auth
Routes take `student_id` as a query param and auto-create a placeholder `User`/`Student`
(email `student_{id}@example.test`, `hashed_password="demo-no-auth"`). This is wired to real
auth + DPDP consent in Phase 5; do not treat the id as authenticated.

---

# Phase 8 (counsellor dashboard + feedback loop) assumptions

## A16 — Dashboard charts stay dependency-free (no Recharts)
`docs/02_ARCHITECTURE.md` listed Recharts, but the project deliberately ships **no** chart
library: Phase 7 hand-rolled the radar to keep the PWA bundle lean and the render
deterministic, and Phase 8 keeps that convention with `components/BucketChart.tsx`
(horizontal bars) instead of pulling Recharts. Minimal-change rule respected — no new
dependency added; the stack line was corrected to match reality.

## A17 — Small-group suppression threshold is 5 distinct students
`analytics_svc.MIN_GROUP = 5`: every aggregate (RIASEC distribution, top trades,
district demand-mismatch, resistance topic/district/trade buckets) drops any bucket
backed by fewer than 5 distinct students and reports only how many were hidden
(`suppressed_groups`). The PS/eval plan does not fix a k-anonymity number, so 5 is the
customary public-health-dashboard floor; it is a single constant, trivially tunable.

## A18 — "District demand mismatch" interpretation
The PS asks for regional insight but never defines "mismatch" concretely. Phase 8 reads it
as: per district, the count of students, the most-recommended trade, and total
recommendations — surfaced so a counsellor can spot a district funnelling everyone into one
trade. It is a descriptive aggregate over stored recommendations, **not** a comparison to
real labour-market vacancy data (that data is demo, per A5), so the table carries no
real-demand claim.

## A19 — Audit trail is append-only and never stores deleted payloads
`audit_logs` records `override` and `data_deletion` events. A deletion row stores only
*that* and *by whom* a student was deleted (`entity_id` = the id, `detail` = role/actor),
never the removed personal data — otherwise deleting a student would silently retain their
PII (DPDP). The counsellor audit view is scoped to their own cohort's `student` entries;
admins see the full trail.

## A20 — Feedback retraining export is isolated from eval/gold
`POST /feedback` stores helpful/chosen + a Phase 7 sentiment topic + `model_version`; 
`feedback_export_svc` folds this into `data/processed/retrain_feedback.jsonl` (relevance:
2 = chosen, 1 = helpful, 0 = neither) for a *future* ranker retrain. It never writes into
`eval/gold/` — the held-out evaluation set stays untouched so retraining on live feedback
cannot leak into the metrics (RULES: eval stays independent).


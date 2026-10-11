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

---

# Phase 9 (hardening, privacy, deployment, final audit) assumptions

## A21 — Production demo stays on SQLite (single node); Postgres is a driver swap
`docs/02_ARCHITECTURE.md` names Postgres for prod, but no PG driver is in
`requirements.txt` and the acceptance target is "works on a clean machine with one
command". The prod stack therefore runs the app's SQLAlchemy engine against a
**SQLite file on a named Docker volume** (`DATABASE_URL=sqlite:////data/...`), with
consistent online-backups (`make backup`). Moving to Postgres is a driver install +
`DATABASE_URL` change — no application code changes (documented in
`infra/env.prod.example`). We did not add a DB server we cannot validate here.

## A22 — ML/web dependency advisories are documented, not force-upgraded
`make security` (pip-audit) flags transitive advisories (`starlette` via FastAPI,
`transformers` via sentence-transformers, `pyasn1`/`ecdsa` via python-jose) and ML
pickle/DoS notes (`lightgbm`, `scikit-learn`). We bumped only the two **safe, direct,
high-value** pins (`python-multipart` 0.0.12→0.0.31, `python-jose` 3.3.0→3.4.0) and
froze the rest: upgrading the ML stack is a coordinated major migration that must be
re-validated against the eval gates, so slipping it in at the release freeze trades a
reproducible build for unquantified risk. Every remaining advisory is recorded with a
threat-model rationale in `docs/SECURITY.md` rather than hidden. (The HS256-only JWT
means the ECDSA/ASN.1 code paths are never executed.)

## A23 — R12 accessibility is an automated audit, not a WCAG-AA certification
PS R12 ("design for low-literacy / low-digital-familiarity users") was held at 0.5 in
earlier phases for being "designed-for but not instrumented". Phase 9 instruments it
with a **real axe-core audit in CI** (`frontend/src/components/accessibility.test.tsx`).
Honest scope: jsdom has no layout engine, so `color-contrast` is excluded and there is
**no manual screen-reader / AT testing** and **no Lighthouse score**. R12 is scored 1
because the requirement (design orientation) is met with a running artefact, not
because a full WCAG 2.2 AA conformance claim is made — that would be an overclaim.

## A24 — `ps_audit` 100 % means "every requirement has an artefact", not perfection
The weighted alignment in `docs/PS_TRACEABILITY.md` is **self-scored** against the PS
with the rule that any row marked complete must cite real evidence (a test, an eval
gate, or a demo artefact); `scripts/ps_audit.py` fails the run otherwise. The score is
reproducible but the weights (3 = explicit, 2 = implied, 1 = nice-to-have) are a
judgement call, so 100 % is read as "implemented + evidenced", with the persistent
limitations (demo outcome data, synthetic labels, coverage gap) stated on the same page.

## A25 — `make demo` serves locally; the Docker prod stack is the separate path
The acceptance line is "`make demo` works on a clean machine". It runs
`alembic upgrade head` + `seed_all` + `uvicorn` against the local venv (verified on a
fresh DB) and is **offline-safe** (deterministic fallback scorer, no-op loaders, no
model download). It does not require Docker (unavailable in the build environment);
the hardened container path is provided and separately validated as YAML via
`docker-compose.prod.yml` + `infra/nginx.conf`.

## A26 — Single-origin Nginx; CSP allows inline styles but not inline scripts
The SPA is built with `VITE_API_BASE=/api` and Nginx reverse-proxies `/api` -> the
backend, so the browser makes **no cross-origin calls** and needs no client CORS.
The CSP (`script-src 'self'`) forbids inline/eval scripts (the app ships none) but
permits `style-src 'unsafe-inline'` because React sets inline `style` attributes on
elements; this is a deliberate, documented narrowing rather than a blanket `'unsafe-inline'`.

---

# Phase 10 (truth reset and spec lock) assumptions

## A27 — Honest re-score against PS wording
An independent gap analysis (see `KaushalPath_SIH26241_Gap_Analysis_and_Phase_Plan.docx`)
re-scored PS alignment at ~60% (26.0 / 43 weighted). The previous 100% score
checked only that evidence text existed, not whether it matched the PS wording.
Rows R1–R10, R12, R14 are set to 0.5 with a one-line reason each. Five new rows
(R16–R20) capture capabilities the PS implies but were not in the original sheet.
The 0.97 gate intentionally fails until Phases 11–18 ship the missing capabilities.

## A28 — Duplicate i18n bootstrap removed
Two i18n initialisations existed: `src/i18n/config.ts` (using `locales/*.json`)
and `src/i18n/index.ts` (using sibling `en.json`/`hi.json` with only Phase 0
keys). The duplicate `index.ts` and its `en.json`/`hi.json` have been deleted.
Only `config.ts` + `locales/en.json` + `locales/hi.json` remain. `main.tsx` and
all tests import `./i18n/config`.

## A29 — PS deadline and portal verification
The gap analysis notes that sih.gov.in blocks automated requests and the PS text
was cross-checked on title, ministry and theme only. PS_SPEC.md says deadline
5 Oct 2026 (already past at time of Phase 10). We are building for the prototype
demonstration at evaluation. The team should re-confirm the PS wording against the
portal when access is available.

---

# Phase 19 (data foundation) assumptions

## A30 — Provenance and Evidence Grades (A–D)
Every row across reference data tables (`occupations`, `courses`, `centres`, `market`,
`provider_outcomes`, `trades`) must carry full provenance metadata (`source`,
`source_url`, `source_year`, `retrieved_on`, `licence`, `is_demo`, `evidence_grade`, `n`).
Grades follow a strict 4-tier hierarchy:
- **Grade A:** Statistically designed government/official microdata/standards (e.g. O*NET, NCVET QP, NCO-2015, DGT ITI grading, Scheme guidelines).
- **Grade B:** Tracer studies, administrative portal outputs (e.g. DGT STRIVE tracer, PMKVY placements, ASER 2023).
- **Grade C:** Large-sample surveys or uncalibrated national datasets (e.g. PLFS microdata).
- **Grade D:** Synthetic / demo seed rows.
Synthetically seeded rows are strictly flagged `is_demo=True` and assigned Grade D.
Per the age decay rule, data older than 3 years (`current_year - source_year > 3`) drops
one grade level (A -> B, B -> C, C -> D).

## A31 — Evidence Precedence and Minimum Cell Size Gate (n >= 30)
When selecting evidence for display or ranking, Grade A strictly outranks Grade B,
Grade B outranks Grade C, and Grade C outranks Grade D. Estimates from different evidence
grades are never averaged or combined. Under the same grade, geographic resolution
follows `provider -> district -> state -> national`. Any estimate with cell size
`n < 30` cannot be shown or ranked, triggering automatic fallback to the next broader
geographic level. If no row satisfies the `n >= 30` gate, the system returns
`(None, "no_verified_data")` rather than fabricating numbers.

## A32 — Canonical Trade Entity Resolution Threshold (>= 92)
Entity matching against canonical vocational trades (`trades`) executes a multi-stage
resolution cascade:
1. Exact NCVT trade code or QP qualification code match (`confidence=1.0`, official).
2. Exact NCO-2015 code match (`confidence=0.98`, official).
3. Exact normalized name match (`confidence=0.95`, name_match).
4. Fuzzy token-set ratio >= 92 (`confidence=score/100`, fuzzy).
Any fuzzy match at or above 92 is flagged with `needs_review=True` and recorded in
`backend/app/data/processed/trade_crosswalk_review.csv` for human curation. Any candidate
below 92 is rejected (`needs_review=False`) and never linked to canonical entities.

## A33 — Local Government Directory (LGD) Geography Standards
Learner and provider geographic locations are mapped against LGD codes across 37
canonical states/UTs and key vocational districts. Any unrecognized state or district
is recorded in `backend/app/data/processed/geo_rejects.csv` without automated guessing.
When falling back to state level from an unmatched or small-cell district, state-wide
aggregate records (`district is None`) are prioritized over arbitrary sibling districts.

---

# Phase 20 (grounded aptitude & ability requirements) assumptions

## A34 — Grounded Aptitude Requirements & O*NET Ability Concordance
Resolves audit Finding 2 (`aptitude_fit` previously evaluated to the identical mean of student
scores across every candidate career, wasting its 0.15 weight). In Phase 20, aptitude fit is
grounded in empirical trade-specific ability profiles (`occupation_abilities`, O*NET 31.0 Abilities
and Knowledge, Grade A, n >= 30).
- **Core Dimensions:** 4 vocational dimensions (`required_num`, `required_verbal`,
  `required_spatial`, `required_mech`), normalized on a 0.0–1.0 scale.
- **Requirement-Weighted Concordance:**
  `weighted_score = sum(r_d * s_d) / sum(r_d)` across the 4 dimensions. Trades heavily
  demanding mechanical and spatial reasoning (e.g. Welder, Fitter) reward student manual and spatial
  dexterity while deprioritizing irrelevant verbal scores.
- **Primary Ability Alignment:** Trades define a distinguishing `primary_ability` (e.g. 'mech'
  for mechanics/welders, 'num' for data entry/accounting, 'verbal' for healthcare/counselling,
  'spatial' for drafting/design). Composite fit blends `0.7 * weighted_score + 0.3 * primary_ratio`.
- **Explainability Transparency:** When `aptitude_fit > 0.70`, `generate_reason_codes` surfaces
  the specific primary dimension (`APTITUDE_STRONG_DIM`) with `"O*NET Abilities (Grade A)"`
  provenance badge in English and Hindi.
- **Graceful Fallback:** When an occupation carries no ability requirement record,
  `compute_aptitude_fit` falls back to the mean of student aptitude scores.

## A35 — O*NET 31.0 Career Interests Normalization Formula & High-Point Codes
O*NET 31.0 long-format `Career Interest Types.txt` is pivoted to provide per-occupation
RIASEC vectors. Per O*NET Scales Reference:
- **Scale OI (Occupational Interests):** Min 1.0, Max 7.0. Rescaling formula to [0.0, 1.0]:
  `norm_oi = (val - 1.0) / 6.0`, strictly bounded to [0.0, 1.0].
- **Scale IH (High-Point Codes):** High-point codes 1=R, 2=I, 3=A, 4=S, 5=E, 6=C, 0=None
  are captured for first, second, and third interest high-points.
- Provenance: Stored as `source='onet_interests'`, `evidence_grade='A'`, `is_demo=False`,
  `retrieved_on='2026-10-11'`. Sample size `n` and `standard_error` remain NULL (per data dictionary).

## A36 — Construct Requirement Formula & Content Model Validation
Cognitive and vocational ability requirements are derived from `Abilities.txt` and `Knowledge.txt`
using construct mappings in `backend/app/data/raw/aptitude_map.yaml`:
- **Formula:** `requirement = sqrt(norm_importance * norm_level)` averaged over mapped elements.
  - `norm_importance = (IM - 1.0) / 4.0` (Scale IM: 1.0 - 5.0)
  - `norm_level = LV / 7.0` (Scale LV: 0.0 - 7.0)
- **Validation:** Element names in `aptitude_map.yaml` are verified against `Content Model Reference.txt`
  and fail loudly (`ValueError`) if any unknown element is encountered.
- **Primary Ability:** Construct with the highest requirement score.

## A37 — Family Safety Work Context Flags (Soft Filtering Only)
Environmental and physical characteristics from O*NET 31.0 `Work Context.txt` are evaluated
against thresholds in `work_flags.yaml` and written to `occupations.work_flags` JSON:
- `{outdoor, hazard, physical_effort, customer_contact}`
- **Fairness Guarantee:** Work flags address parental and learner safety questions and drive
  an optional SOFT learner preference. They are NEVER a hard filter and NEVER gated by gender.

## A38 — O*NET-to-India Trade Concordance, Job Zone & RIASEC Spread Reviews
- **Precedence Hierarchy:** PS-provided (Tier 1) > O*NET-derived (Tier 2, Grade A) > Curated Demo
  (Tier 3, Grade D). Unmapped trades retain demo values (`is_demo=True`, Grade D). Never blend
  demo and real values inside one vector.
- **Coverage:** 103 of 135 vocational trades (76.3%) achieve Grade-A empirical grounding,
  exceeding the >= 70% target.
- **Spread Flag:** When aggregating across multiple O*NET codes for a trade, if the sample
  standard deviation of any RIASEC dimension exceeds 0.2, the trade is flagged with `needs_review=True`
  and written to `data/processed/riasec_spread_review.csv`.
- **Job Zone Sanity Check:** Mismatches between O*NET Job Zones (1-5) and NSQF levels are written
  to `data/processed/jobzone_nsqf_review.csv` for human review (report only, never auto-corrected).
- **Hindi Titles:** Retained from NCVT/NSDC titles in `occupations.csv`, avoiding ESCO machine translation.
- **Licence Attribution:** O*NET 31.0 is licensed under CC BY 4.0; official attribution notice is
  documented in `docs/ATTRIBUTION.md`.

---

# Phase 21 (Assessment v2 Grounded Items, 2PL IRT Calibration & Aptitude Fit) Assumptions

## A39 — 2PL IRT Calibration Model Details & Calibration Sample Threshold
Item calibration uses a Two-Parameter Logistic (2PL) Item Response Theory model:
$$P(Y_{ij} = 1 \mid \theta_i) = \frac{1}{1 + e^{-a_j (\theta_i - b_j)}}$$
- **Parameters:** Discrimination $a_j \in [0.2, 3.0]$ and Difficulty $b_j \in [-3.0, 3.0]$.
- **Calibration Engine:** Marginal Maximum Likelihood (MML) via Expectation-Maximization (EM)
  with Gauss-Hermite numerical quadrature over standard latent distribution $\theta \sim \mathcal{N}(0, 1)$.
- **Operational Sample Threshold ($n \ge 300$):** Real-world item parameter updates require at least
  300 respondent observations per item. In initial development and before field pilots, `calibrate_items.py`
  runs with synthetic respondent simulations recovering parameters within $|\Delta a|, |\Delta b| \le 0.25$,
  or seeds calibrated values with Bayesian priors centered on curricular bands.
- **Adaptive Selection:** Items are indexed and selected by Fisher information distance weighted by
  calibrated discrimination parameter $a_j$, picking maximally informative items close to current latent $\theta$.

## A40 — Forced-Choice Tie-Break Rule (1 SEM Threshold, Max 3 Pairs)
- **Contested Criterion:** After the adaptive Likert phase, if the score difference between any top-3
  adjacent dimensions (or the rank-3 vs rank-4 boundary dimension) is within 1 Standard Error of
  Measurement ($\Delta \le \max(\text{SEM}_a, \text{SEM}_b)$), the pair is classified as contested.
- **Forced-Choice Mechanism:** The engine serves forced-choice pairwise comparison items (`item_type='pair'`)
  asking respondents to choose between two concrete trade-contextualized activities (`dim_a` vs `dim_b`).
- **Score Adjustment:** Selecting option A boosts `dim_a` and adjusts `dim_b` on the running signed scale,
  resolving ambiguous boundary ties.
- **Item Budget & Safety Cap:** Tie-break items are capped at `MAX_TIE_BREAKS = 3` pairs. Combined
  interest Likert items and tie-break pairs are strictly capped at `HARD_CAP = 30` items to maintain
  learner focus and prevent assessment fatigue.

## A41 — Pure Aptitude Fit Function: Shortfall Only, Surplus Unpenalized & SE Shrinkage
The cognitive and vocational aptitude matching function (`aptitude_match` in `app.ml.ranking.aptitude_fit`):
- **Percentile Linking Default:** Normalizes raw aptitude scores against normative percentiles
  anchored to ASER 2023 foundational numeracy/literacy bands.
- **One-Sided Shortfall:** Penalizes only shortfall below occupational requirement:
  $$\text{shortfall}_c = \max(0.0, \text{requirement}_c - \theta_c)$$
  Surplus ability is never penalized ($\text{shortfall}_c = 0.0$ when $\theta_c \ge \text{requirement}_c$).
- **Measurement Uncertainty Shrinkage:** When standard error $\text{SE}_c$ is high, confidence is discounted
  ($\text{confidence} = \prod (1 - \min(1.0, 2 \cdot \text{SE}_c))$) and the raw fit score shrinks toward
  the uninformative neutral midpoint 0.50 via Bayesian reliability weighting:
  $$\text{score} = \text{confidence} \cdot \text{raw\_fit} + (1 - \text{confidence}) \cdot 0.50$$

## A42 — Validity Study Harness & G4 Agreement Numbers (Simulated Baseline)
- **Validity Suite:** `scripts/validity_studies.py` evaluates test-retest reliability ($r \ge 0.70$),
  convergent validity against vocational inventory benchmarks ($r \ge 0.60$), and known-groups criterion
  validity (AUC $\ge 0.75$ across trade tracks).
- **G4 Agreement (Simulated):** On 200 synthetic respondents (`eval/scripts/sim_assessment.py`),
  top-3 letter set agreement achieves **96.5%** (target $\ge 95\%$) with exact-order agreement at
  **89.5%** (exceeding the 74% unadjusted baseline), requiring an average of 22.9 interest items
  (target $\le 24$, max 27). Labelled simulated until field pilot survey collection.



# Changelog

All notable changes to the KaushalPath vocational career counselling and family decision support platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Phase 30] — 2026-10-19: Final Pre-Submission Verification Lock & Audit Certification

### Added
- Appended reproducible pre-submission verification log and real command terminal outputs to `docs/EVAL_REPORT.md` (covering `make check`, `make eval-final`, `make ps-audit`, `make security`, `demo_preflight.py`, and `data_provenance_audit.py`).
- Isolated Alembic migration lifecycle tests in `test_phase19_foundation.py` to prevent development database table drops.
- Wired outcome evidence ingestion (DGT STRIVE, PLFS, PMKVY, ITI scorecards) into `scripts/seed_all.py` for automated reproducible seeding.
- Tagged release snapshot `sih2026-submission`.

### Verified
- **PS Traceability:** 100.0% alignment (57.0 / 57.0 weighted score) verified by `python scripts/ps_audit.py`.
- **Backend Test Suite:** 213 of 213 tests passing across unit and integration suites (`pytest backend`).
- **Frontend Test Suite:** 39 of 39 tests passing with zero regressions (`npm --prefix frontend test`).
- **Linters:** Zero lint errors across backend, scripts, and frontend (`ruff check`, `tsc --noEmit`).
- **Multi-Period Outcome Evidence Backtest:** 834 transitions evaluated, 76.3% 80-credible-interval coverage (within pre-registered 70%–90% target).
- **Stage Demo Preflight:** All 7 stages passed in 26.81s (well below 60.0s threshold).

---

## [Phase 29] — 2026-10-18: Demo Script & Technical Q&A Hardening

### Added
- `docs/DEMO_SCRIPT.md`: Step-by-step stage demo protocol covering 8 key presentation moments (adaptive assessment, multi-signal recommendation, grounded conversation, live escalation, admin heat matrix) with contingency fallbacks.
- `docs/QA_ANSWERS.md`: 12 rigorous judge Q&A defenses addressing data leakage, rater subjectivity, k>=5 differential privacy, counter-factual fairness, and cold-start handling.
- Enhanced `scripts/demo_preflight.py` with multi-step in-process verification to validate full end-to-end functionality before live stage demonstrations.

---

## [Phase 28] — 2026-10-18: Evaluation-Day MSDE Dataset Ingestion Drill (PS Row R14)

### Added
- `scripts/load_provided_dataset.py`: Flexible ingestion loader supporting dynamic CSV schemas, fuzzy header normalization, and custom `mapping.yaml` overrides.
- Automated unmapped column logging to `data/processed/provided_unmapped_columns.csv`.
- `docs/MSDE_DAY_RUNBOOK.md`: 10-minute on-stage evaluation runbook for ingesting judge-provided CSV files under pressure.
- `backend/tests/integration/test_phase28_msde_ingestion.py`: Test suite validating ingestion of snake_case, Title Case, and messy format CSV variants.
- Verified PS Row R14 closed to status 1.0.

---

## [Phase 27] — 2026-10-18: LLM Fallback & Anti-Hallucination Hardening

### Added
- Strict numerical fact validator (`app/services/conversation/validator.py`) detecting invented salaries, placement rates, fees, or duration numbers in LLM responses.
- Automatic fallback mechanism: when candidate LLM replies introduce ungrounded statistics or fail schema validation, the conversation engine falls back to verified DB-grounded templates.
- Unit and integration test coverage (`backend/tests/unit/test_phase27_llm_fallback.py`) validating zero-hallucination tolerance.

---

## [Phase 26] — 2026-10-18: Household Income-Band Tailoring (PS Row R7)

### Added
- Persisted and validated learner `income_band` (`low`, `mid`, `high`) across registration, assessment, and database schema.
- Affordability feature extraction in multi-signal ranker calculating net fee relative to household budget constraints.
- Transparent rule-based reason codes: `AFFORDABLE_FOR_INCOME_BAND` and `HIGH_FEE_RELATIVE_TO_INCOME_BAND` in Hindi and English.
- Rule-based conversation branching in `responder.py` tailoring objection replies based on household income tier (e.g. leading with stipends/fee waivers for low-income vs NSQF progression for high-income).
- Closed PS Row R7 to status 1.0 (elevating overall traceability score to 100.0%).

---

## [Phase 25] — 2026-10-18: Evaluation Report Relabeling & De-circularized Expert Gold

### Added
- Replaced circular latent score with independent, hand-authored vocational counselling rubric (`eval/gold/rubric.md`, `eval/gold/METHODS.md`).
- Explicit provenance labeling across all evaluation report tables (`[DEMO]`, `SYNTHETIC`, `REAL`).
- Automated data provenance audit (`scripts/data_provenance_audit.py`) wired into `make check` to ensure no synthetic metric is presented as real-world field validation.

---

## [Phase 18] — 2026-10-15: Initial Baseline Audit & Core Platform Foundation

- Completed baseline vocational guidance engine with adaptive assessment, hybrid ranker, Family Room collaboration, and admin resistance dashboard.

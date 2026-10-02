# PS Traceability Matrix — target alignment >= 97%

> STATUS: rows below are derived from the **inferred scope** in `docs/01_PS_ANALYSIS.md`, because the
> official PSID 26241 text is not yet in `docs/PS_SPEC.md` (see `docs/ASSUMPTIONS.md` A1).
> Before the Phase 0 gate is truly locked, re-run Phase 0 task 1 against the official PS and replace the
> "Requirement" wording with direct quotes, then confirm weights.
> Weight: 3 = explicitly stated in PS, 2 = implied, 1 = nice-to-have. Status: 0 / 0.5 / 1.
> Score = sum(weight*status)/sum(weight).

| ID | Requirement (from PS once pasted) | Weight | Feature/Module | Test or evidence | Status |
|---|---|---|---|---|---|
| R1 | AI career counselling for vocational students (adaptive interest + aptitude assessment) | 3 | ml/assessment + api/routes/assessment | G4 sim (>=95% agreement) + e2e | 0 |
| R2 | Recommends top-3 careers/courses with ranking | 3 | ml/retrieval + ml/ranking + /recommend | G2 Top-3 hit >=95%, G3 NDCG@5 >=0.90 | 0 |
| R3 | Family / parent decision support (Family Decision Room: weights, compare, vote, consensus) | 3 | services/room_svc + /rooms + Phase 7 UI | e2e demo path | 0 |
| R4 | Explainable recommendations (reason codes + data source, no black box) | 3 | ml/explain + /recommend | G5 explanation coverage = 100% | 0 |
| R5 | Hard eligibility/age/NSQF/budget/district enforced as rules, not ML | 3 | ml/ranking/filters.py | G1 violations = 0%, property test | 0 |
| R6 | Uses the datasets provided on the official PS page | 3 | Phase 1 loaders (scripts/) | data_report row counts + source | 0 |
| R7 | Roadmap: course -> training centre -> certification/NSQF -> placement | 2 | services/roadmap_svc + /roadmap | e2e | 0 |
| R8 | Vernacular (Hindi + English) + accessible + low-bandwidth PWA | 2 | frontend i18n + a11y + PWA | Lighthouse a11y >=90, missing-keys=0 | 0 |
| R9 | No fabricated data presented as real (source, year, is_demo) | 2 | data layer + SourceBadge | loader tests + UI badge check | 0 |
| R10 | Fairness: no caste/religion/gender features; bias slice report | 2 | ml/ranking/features + eval slices | G6 slice gap <=3 pts | 0 |
| R11 | Counsellor cohort dashboard + override + feedback loop | 2 | api/routes/counsellor + Phase 8 UI | role-based access tests | 0 |
| R12 | Privacy/consent (DPDP-style): consent screen, minimal data, delete-my-data | 1 | auth consent + DELETE /students/me | deletion test + docs/PRIVACY.md | 0 |
| R13 | Scalable / deployable (dockerized, CI) | 1 | Docker + docker-compose + GitHub Actions | `docker compose up`, CI green | 0 |
| R14 | Measurable, reproducible accuracy claim (>=95% on documented gates) | 2 | eval harness (Phase 4) | `make eval` report saved | 0 |
| R15 | Multilingual voice input (Whisper) | 1 | optional, post-MVP | manual demo | 0 |

Placeholder rows removed: 0 remaining.
Current weighted score: 0 / 34 = 0.00 (all status 0 at Phase 0).
Final audit (Phase 9): any row < 1 must have a written reason; total must be >= 0.97.

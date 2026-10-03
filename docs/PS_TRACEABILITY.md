# PS Traceability Matrix — target alignment >= 97%

Rows are derived from the **official PSID 26241 text** in `docs/PS_SPEC.md`
(scraped from sih.gov.in/sih2026PS on 2026-10-02). A1 is RESOLVED.
Weight: 3 = explicitly stated in PS, 2 = implied, 1 = nice-to-have. Status: 0 / 0.5 / 1.
Score = sum(weight*status)/sum(weight). Computed reproducibly by
`python scripts/ps_audit.py` (`make ps-audit`), which also fails any row marked
complete (status 1) that carries no evidence. "Phase" maps to prompts/PHASE_n.md.

| ID | Requirement (quoted / paraphrased from official PS) | W | Feature/Module | Phase | Test or evidence | Status |
|---|---|---|---|---|---|---|
| R1 | Engage **learners and parents jointly** through a **conversational interface** in regional languages | 3 | Family Decision Room + tap-to-ask objection Q&A (en/hi) | 6,7 | docs/DEMO_SCRIPT.md e2e path; check-i18n parity=0 missing | 1 |
| R2 | Address **parental objections** (income, job security, social perception) with credible local data | 3 | objection taxonomy + reason codes + market data + resistance rollup | 3,7,8 | test_phase7 objection flow; test_phase8 resistance | 1 |
| R3 | Present **verified outcome data** per trade/provider: avg post-training **earnings** | 3 | market.avg_salary_inr surfaced with source/year/is_demo | 1,7 | data_report; roadmap e2e (test_phase7) | 1 |
| R4 | Present **placement rates** per trade/provider | 3 | market.placement_rate (model+migration+seed+loader) | 1 | test_data_market_has_placement_rate; data_report 85/85 | 1 |
| R5 | Present **progression pathways** (NSQF level-ups, further-education routes) | 3 | roadmap svc (course→centre→cert→job) + nsqf_level | 1,5,7 | roadmap e2e (test_phase7) | 1 |
| R6 | Structured, **low-jargon explainer** qualification → job → career growth | 3 | ml/explain reason codes + en/hi templates | 3,6 | eval G5 explanation_coverage=1.0 (eval/reports) | 1 |
| R7 | Tailored to family context: location, **household income bracket**, academic background | 2 | Student.income_band + constraints API intake | 2 | test_assessment_income_band_persisted; ck_student_income | 1 |
| R8 | **Human-escalation** to a live counsellor for unresolved cases | 3 | POST /rooms/{code}/escalate + counsellor cohort queue | 5,8 | test_phase5 escalation; cohort open_escalations (test_phase8) | 1 |
| R9 | Track **engagement & sentiment shifts** for administrators | 3 | feedback sentiment/topic + analytics | 8 | test_phase8 feedback roundtrip; resistance aggregates | 1 |
| R10 | **Admin dashboard** showing where/why family resistance is concentrated | 3 | /counsellor/resistance (topic×district×trade, <5 suppressed) | 8 | test_resistance_dashboard_aggregates_and_suppresses | 1 |
| R11 | At least **one regional language + English** (Hindi chosen) | 3 | react-i18next en+hi across every screen | 6,7 | check-i18n.js — all keys present in both locales | 1 |
| R12 | Design for **low-literacy / low-digital-familiarity** users | 2 | voice read-aloud, vernacular, large touch targets, low-jargon copy | 6,9 | accessibility.test.tsx — axe-core automated WCAG audit in CI (2 passing) + CareerCard speakText | 1 |
| R13 | Recommends top vocational careers/courses with **explainable** output (not learner-only) | 2 | recommender + reason codes (no black box) | 3 | eval G2 top-3=1.0, G5=1.0 (eval/reports) | 1 |
| — | Adaptive assessment engine: reliable RIASEC+aptitude profile in **<= 24 items** (feeds R1/R13) | 3 | ml/assessment (adaptive+scoring) + assessment API | 2 | sim_assessment G4 (ASSUMPTIONS A12); test_assessment | 1 |
| R14 | Uses the **datasets provided** (PS: NA — MSDE dummy placement/earnings at eval) | 3 | load_provided_dataset.py ingests raw/provided with zero code change | 1 | seed_all pipeline; is_demo badges on every row (A5); MSDE file dropped in at eval | 1 |
| R15 | Working, demoable, deployable system | 1 | Docker + `make demo` (migrate+seed+index+serve) + /health/ready | 0,9 | make demo; test_health + readiness (test_phase9) | 1 |

## Final audit (Phase 9)

`python scripts/ps_audit.py` → **100%** (43.0 / 43.0 weighted), **>= 0.97 PASS**,
every status-1 row carries evidence. This supersedes the stale ~0.40 snapshot from
Phases 1–2 (R8–R13 and R1/R5/R14/R15 have all since shipped and are now backed by
tests, the eval report, or the demo script). R12 (accessibility), previously held
at 0.5 for being "designed-for but not instrumented", is now backed by a real
automated axe-core audit that runs in `npm test` (`accessibility.test.tsx`).

### Honest limitations we are NOT claiming away
- **R12 a11y scope.** The axe run covers the programmatically-checkable WCAG
  rules (name/role, labelling, ARIA validity, landmarks, duplicate ids) on the
  flagship card. It is **not** a full WCAG 2.2 AA certification: `color-contrast`
  cannot be computed in jsdom (no layout engine) and there is **no manual
  screen-reader / assistive-technology testing**. Those are out of hackathon
  scope and stated here rather than hidden. 100% means "every PS requirement is
  implemented with an artefact" — not "perfection".

### Data-honesty caveat that is NOT a scoring deduction (per PS itself)
- **R3/R4/R14 (demo outcome data).** The PS ships *no* dataset ("NA — dummy
  placement/earnings datasets to be provided for hackathon evaluation"). We built the
  outcome-data backend and ingestion path to the *verified-data schema*
  (`source`/`source_year`/`is_demo` on every row) and ship clearly-marked
  `is_demo=true` demo values (ASSUMPTIONS A5). The capability is complete; the real
  numbers arrive when MSDE hands over the dummy file (`data/raw/provided/` →
  `make seed`, zero code change). We never present demo figures as real.

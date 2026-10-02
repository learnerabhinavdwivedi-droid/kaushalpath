# PS Traceability Matrix — target alignment >= 97%

Rows are now derived from the **official PSID 26241 text** in `docs/PS_SPEC.md`
(scraped from sih.gov.in/sih2026PS on 2026-10-02). A1 is RESOLVED.
Weight: 3 = explicitly stated in PS, 2 = implied, 1 = nice-to-have. Status: 0 / 0.5 / 1.
Score = sum(weight*status)/sum(weight). "Phase" maps to prompts/PHASE_n.md.

| ID | Requirement (quoted / paraphrased from official PS) | W | Feature/Module | Phase | Test or evidence | Status |
|---|---|---|---|---|---|---|
| R1 | Engage **learners and parents jointly** through a **conversational interface** in regional languages | 3 | Family Room + conversational UI | 6,7 | e2e demo path | 0 |
| R2 | Address **parental objections** (income potential, job security, social perception) with credible local data | 3 | objection-explainer / reason codes + market data | 3,7 | compare view + talk points | 0 |
| R3 | Present **verified outcome data** per trade/provider: avg post-training **earnings** | 3 | market.avg_salary_inr | 1 | data_report, roadmap | 0.5 |
| R4 | Present **placement rates** per trade/provider | 3 | market.placement_rate (added: model+migration+seed+loader) | 1 | data_report 85/85, test_data_market_has_placement_rate | 1 |
| R5 | Present **progression pathways** (NSQF level-ups, further-education routes) | 3 | roadmap svc + nsqf_level | 1,5 | roadmap e2e | 0.5 |
| R6 | Structured, **low-jargon explainer** qualification → job → career growth | 3 | explain/reason_codes + templates | 3 | G5 coverage | 0 |
| R7 | Tailored to family context: location, **household income bracket**, academic background | 2 | student.income_band + constraints API intake | 2 | test_assessment_income_band_persisted, ck_student_income | 1 |
| R8 | **Human-escalation** to a live counsellor for unresolved cases | 3 | escalation flow + counsellor queue (no explicit flow yet) | 5,8 | integration test | 0 |
| R9 | Track **engagement & sentiment shifts** for administrators | 3 | feedback/sentiment capture (no sentiment field yet — see A10) | 8 | analytics | 0 |
| R10 | **Admin dashboard** showing where/why family resistance is concentrated | 3 | admin/cohort dashboard | 8 | dashboard render | 0 |
| R11 | At least **one regional language + English** (Hindi chosen) | 3 | react-i18next en+hi | 6,7 | missing-i18n-keys = 0 | 0.5 |
| R12 | Design for **low-literacy / low-digital-familiarity** users | 2 | a11y tokens, big buttons, read-aloud | 6 | Lighthouse a11y >= 90 | 0 |
| R13 | Recommends top vocational careers/courses with **explainable** output (background: not learner-only) | 2 | recommender + reason codes | 3 | eval G2/G5 | 0 |
| — | Adaptive assessment engine: reliable RIASEC+aptitude profile in **<= 24 items** (feeds R1/R13) | 3 | ml/assessment (adaptive+scoring) + assessment API | 2 | sim_assessment G4 + test_assessment | 1 |
| R14 | Uses the **datasets provided** (PS: NA — MSDE dummy placement/earnings at eval) | 3 | Phase 1 loaders ingest raw/provided | 1 | seed + is_demo badges | 0.5 |
| R15 | Working, demoable, deployable system | 1 | Docker + CI + `make demo` | 0,9 | `docker compose up` | 0.5 |

## Coverage gaps found while verifying the official PS (fix before/at noted phase)
- **R4 placement_rate** — RESOLVED (Phase 1): `placement_rate` Float added to `Market` model +
  initial migration + `market.csv` demo column (85/85) + `load_market.py`; covered in
  `data_report.py` and asserted by `test_data_market_has_placement_rate`.
- **R9 sentiment / R8 escalation** — no fields/flow exist. Add an `objection`/`sentiment`
  capture on feedback + a student-initiated "escalate to counsellor" flag on rooms. → Phase 5/8.
- **R7 household income bracket** — RESOLVED (Phase 2): `income_band` on `Student` (CHECK
  `ck_student_income`), captured via `POST /assessment/student`, covered by
  `test_assessment_income_band_persisted`.
- **R1 conversational interface** — current plan is structured assessment + room; PS asks for
  a *conversational* surface. Add a template-backed objection Q&A (LLM may only verbalise,
  per non-negotiable #4). → Phase 6/7.

Final audit (Phase 9): re-verify each row against `docs/PS_SPEC.md` with evidence links; any
row < 1 must have a written reason; total must reach >= 0.97. Current snapshot ~0.40 (Phases 1–2
complete: data layer + placement_rate, income_band, and the adaptive assessment engine / G4) —
honest progress, not a missed threshold.

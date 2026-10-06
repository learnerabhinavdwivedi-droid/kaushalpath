# PS Traceability Matrix — honest re-score (Phase 10 truth reset)

Rows are derived from the **official PSID 26241 text** in `docs/PS_SPEC.md`
(scraped from sih.gov.in/sih2026PS on 2026-10-02). A1 is RESOLVED.
Weight: 3 = explicitly stated in PS, 2 = implied, 1 = nice-to-have. Status: 0 / 0.5 / 1.
Score = sum(weight×status)/sum(weight). Computed reproducibly by
`python scripts/ps_audit.py` (`make ps-audit`), which also fails any row marked
complete (status 1) that carries no evidence. "Phase" maps to prompts/PHASE_n.md.

**Phase 10 re-score rationale:** a row is 1 only if code + test + demo evidence
exist for the *PS wording*, not for a nearby feature. Rows that have partial
implementations are set to 0.5 with a reason. Five new rows (R16–R20) capture
capabilities the PS implies but were missing from the original sheet.

| ID | Requirement (quoted / paraphrased from official PS) | W | Feature/Module | Phase | Test or evidence | Status |
|---|---|---|---|---|---|---|
| R1 | Engage **learners and parents jointly** through a **conversational interface** in regional languages | 3 | Family Room exists (shared code, roles, weights, votes); conversation = AskBox 4 fixed chips, no chat API, no free text, no speech input | 6,7 | Room e2e exists; no conversation test | 0.5 |
| R2 | Address **parental objections** (income, job security, social perception) with credible local data | 3 | Objection taxonomy + 5 topics exist; answers are static templates, not grounded in state/district/provider outcome data | 3,7,8 | test_phase7 objection flow; answers not data-grounded | 0.5 |
| R3 | Present **verified outcome data** per trade/provider: avg post-training **earnings** | 3 | market.avg_salary_inr per (trade, state) only — no provider earnings, no ranges (p25/median/p75) | 1,7 | data_report; no provider-level earnings | 0.5 |
| R4 | Present **placement rates** per trade/provider | 3 | market.placement_rate per (trade, state) only — nothing per provider or per cohort | 1 | test_data_market_has_placement_rate; no provider rates | 0.5 |
| R5 | Present **progression pathways** (NSQF level-ups, further-education routes) | 3 | Roadmap = course → centre → cert → job; nsqf_level shown but no further-education / lateral entry / apprenticeship routes | 1,5,7 | roadmap e2e; no progression table | 0.5 |
| R6 | Structured, **low-jargon explainer** qualification → job → career growth | 3 | Reason codes + en/hi templates good; not tailored by income band or schemes/stipends | 3,6 | eval explanation_coverage; income band not used to shape explainer | 0.5 |
| R7 | Tailored to family context: location, **household income bracket**, academic background | 2 | Student.income_band stored at intake; income band is barely used in answers or recommendations | 2 | test_assessment_income_band_persisted; not used to tailor answers | 0.5 |
| R8 | **Human-escalation** to a live counsellor for unresolved cases | 3 | POST /rooms/{code}/escalate stores free-text reason; no phone, slot, channel, case pack, or routing; unassigned cases invisible to counsellors | 5,8 | test_phase5 escalation; no live connect | 0.5 |
| R9 | Track **engagement & sentiment shifts** for administrators | 3 | Sentiment is user-tapped (manual); no per-message analysis, no trajectory, no "shift" measure | 8 | test_phase8 feedback roundtrip; no automatic sentiment or shift | 0.5 |
| R10 | **Admin dashboard** showing where/why family resistance is concentrated | 3 | /counsellor/resistance: topic × district × trade counts, k<5 suppressed, scoped to counsellor's cohort only; no scheme-admin view, no map, no trend | 8 | test_resistance_dashboard; no scheme-admin scope, no map/trend | 0.5 |
| R11 | At least **one regional language + English** (Hindi chosen) | 3 | react-i18next en + hi across every screen; check-i18n passes | 6,7 | check-i18n.js — all keys present in both locales | 1 |
| R12 | Design for **low-literacy / low-digital-familiarity** users | 2 | Read-aloud (speechSynthesis) in 3 components, large touch targets; no voice input, parents must register with email + password, no PWA PNG icons, no usability evidence | 6,9 | axe-core test on one card; no Lighthouse, no real-browser a11y | 0.5 |
| R13 | Recommends top vocational careers/courses with **explainable** output | 2 | Recommender + reason codes (no black box) — solid | 3 | eval G2 top-3=1.0, G5=1.0 | 1 |
| — | Adaptive assessment engine: reliable RIASEC+aptitude profile in **<= 24 items** | 3 | ml/assessment (adaptive+scoring) + assessment API — solid | 2 | sim_assessment G4; test_assessment | 1 |
| R14 | Uses the **datasets provided** (PS: NA — MSDE dummy placement/earnings at eval) | 3 | load_provided_dataset.py handles occupation columns only; cannot ingest market / provider files; raw/README has stale TODO | 1 | seed_all pipeline; loader cannot ingest MSDE market/provider files | 0.5 |
| R15 | Working, demoable, deployable system | 1 | Docker + `make demo` + /health/ready — solid | 0,9 | make demo; test_health | 1 |
| R16 | Provider-level outcome data (placement rates and earnings per training provider, not just per trade) | 3 | Not implemented — centres carry no outcomes | — | — | 0 |
| R17 | Earnings ranges (p25/median/p75), not single averages | 2 | Not implemented — only avg_salary_inr exists | — | — | 0 |
| R18 | Grounded in-language conversational dialogue (free text, not fixed chips) | 3 | Not implemented — no chat API, no LLM adapter, no free-text understanding | — | — | 0 |
| R19 | Sentiment shift tracking over time (automatic, per-session trajectory) | 3 | Not implemented — sentiment is manual user tap, no shift measure | — | — | 0 |
| R20 | Live human connection with contact details and case pack | 3 | Not implemented — escalation is a DB row with no phone/slot/routing/case-pack | — | — | 0 |

## Phase 10 audit (truth reset)

`python scripts/ps_audit.py` → **~60%** — **FAILS the 0.97 gate**.
This is expected and correct. The score will rise as Phases 11–18 ship.

### What is solid and should be kept
- Adaptive assessment engine (RIASEC + aptitude, eval-gated)
- Hybrid recommender with reason codes and explainability
- Rules-based eligibility (never ML)
- Family Room (weights, votes, consensus)
- Source / year / is_demo provenance on every row
- Privacy-preserving small-group suppression
- Role-based access, audit log
- Hindi UI, Docker, CI, i18n parity

### What needs to be built (Phases 11–18)
- Outcome data backbone with provider-level data (Phase 11)
- Conversation engine backend (Phase 12)
- Sentiment, resistance score and admin analytics API (Phase 13)
- Human escalation with contact and case pack (Phase 14)
- Conversational UI for learner and parent (Phase 15)
- Administrator resistance dashboard v2 (Phase 16)
- Low-literacy and low-bandwidth evidence (Phase 17)
- Evaluation, honest audit and demo (Phase 18)

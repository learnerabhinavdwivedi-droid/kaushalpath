# PS Traceability Matrix — final honest audit (Phase 18)

Rows are derived from the **official PSID 26241 text** in `docs/PS_SPEC.md`
(scraped from sih.gov.in/sih2026PS on 2026-10-02). A1 is RESOLVED.
Weight: 3 = explicitly stated in PS, 2 = implied, 1 = nice-to-have. Status: 0 / 0.5 / 1.
Score = sum(weight×status)/sum(weight). Computed reproducibly by
`python scripts/ps_audit.py` (`make ps-audit`), which also fails any row marked
complete (status 1) that carries no evidence. "Phase" maps to prompts/PHASE_n.md.

**Phase 18 re-score rules (honest):** a row is **1** only when a named automated
test, e2e flow, or an auditable script artefact exists that exercises the *PS
wording* — the evidence cell links to it. A row that is genuinely built but not
yet exercised by an artefact, or built only for one of several dimensions, is kept
at **0.5** with a one-line reason. Nothing was upgraded to 1 without evidence.

| ID | Requirement (quoted / paraphrased from official PS) | W | Feature/Module | Phase | Test or evidence | Status |
|---|---|---|---|---|---|---|
| R1 | Engage **learners and parents jointly** through a **conversational interface** in regional languages | 3 | ChatPanel (learner + parent speaker toggle, free text + voice in/out, grounded FactCards, quick replies, one-tap human hand-off) at /talk and in the Family Room; guest parent joins by room code with no account | 6,7,14,15 | ChatPanel.test.tsx (incl. axe); e2e/talk-hi.spec.ts; test_phase15_guest | 1 |
| R2 | Address **parental objections** (income, job security, social perception) with credible local data | 3 | Conversation engine classifies the objection topic, then grounds the reply in provider/district outcome facts (median/p25/p75, placement, fee) rendered as FactCards with source+year+demo badge | 12,15 | test_phase12_conversation::test_full_turn_hi/test_full_turn_en; run_convo_eval.py | 1 |
| R3 | Present **verified outcome data** per trade/provider: avg post-training **earnings** | 3 | /outcomes returns earnings_p25/median/p75 + placement + fee per trade, sourced from ProviderOutcome with provenance | 11 | test_phase11_outcomes::test_outcomes_api_shape_and_provenance | 1 |
| R4 | Present **placement rates** per trade/provider | 3 | ProviderOutcome.placement_rate per (centre, cohort); surfaced on /providers/{id}/outcomes cohort_outcomes | 11 | test_phase11_outcomes::test_provider_outcomes_endpoint | 1 |
| R5 | Present **progression pathways** (NSQF level-ups, further-education routes) | 3 | ProgressionPath (kind=nsqf_levelup etc., to_label, credit_note) returned in /outcomes progression_paths alongside the course→centre→cert→job roadmap | 5,7,11 | test_phase11_outcomes::test_outcomes_api_shape_and_provenance | 1 |
| R6 | Structured, **low-jargon explainer** qualification → job → career growth | 3 | Reason codes + en/hi templates + roadmap + Scheme (benefit_text en/hi) and apprenticeship stipend now included in the outcome payload | 6,11 | test_phase11_outcomes::test_outcomes_api_shape_and_provenance (schemes); eval explanation_coverage | 1 |
| R7 | Tailored to family context: location, **household income bracket**, academic background | 2 | Location (state/district) and academic background (edu_level) shape grounded facts and eligibility; income_band is captured and carried into the escalation case pack but does NOT yet tailor answers/recommendation scores | 2,7,14 | test_assessment_income_band_persisted; income-band tailoring not exercised | 0.5 |
| R8 | **Human-escalation** to a live counsellor for unresolved cases | 3 | POST /conversations/{id}/escalate builds a case pack, auto-routes to the least-loaded cohort counsellor (else shared pool), full lifecycle open→assigned→contacted→resolved with atomic claim, notifier adapter; /rooms/{code}/escalate is a thin wrapper | 5,8,14 | test_phase14_escalation (pool visibility, atomic claim, lifecycle) | 1 |
| R9 | Track **engagement & sentiment shifts** for administrators | 3 | analyze_sentiment runs per turn; ResistanceSnapshot stores Rs per turn; calculate_shift_label + timeseries give the softened/hardened/unchanged trajectory per conversation and cohort | 13 | test_phase13_resistance_analytics::test_resistance_timeseries_and_map; test_phase13_sentiment_resistance_unit | 1 |
| R10 | **Admin dashboard** showing where/why family resistance is concentrated | 3 | /admin/resistance v2: KPI strip, offline district bubble map, district table, concern×trade heat matrix, 30-day trend, shift bars, top anonymised phrases, filters, CSV export, k<5 suppression | 16 | test_phase16_admin_dashboard; e2e/admin-resistance.spec.ts | 1 |
| R11 | At least **one regional language + English** (Hindi chosen) | 3 | react-i18next en + hi across every screen; conversation + objection KB bilingual | 6,7 | check-i18n.js (parity gate); e2e/talk-hi.spec.ts | 1 |
| R12 | Design for **low-literacy / low-digital-familiarity** users | 2 | Read-aloud (speechSynthesis) on every route, voice input, guest parent join, 3-tap icon onboarding (/start), font-size + high-contrast prefs, PWA PNG + maskable icons, offline banner, real-browser colour-contrast audit | 15,17 | e2e/a11y-contrast.spec.ts; docs/ACCESSIBILITY_EVIDENCE.md; scripts/make_icons.mjs | 1 |
| R13 | Recommends top vocational careers/courses with **explainable** output | 2 | Recommender + reason codes (no black box), vocational filter excludes non-vocational | 3,11 | eval G2 top-3=1.0, G5=1.0; test_phase11_outcomes::test_vocational_filter_in_recommender | 1 |
| — | Adaptive assessment engine: reliable RIASEC+aptitude profile in **<= 24 items** | 3 | ml/assessment (adaptive+scoring) + assessment API | 2 | sim_assessment G4; test_assessment | 1 |
| R14 | Uses the **datasets provided** (PS: NA — MSDE dummy placement/earnings at eval) | 3 | load_provided_dataset ingests market (trade/state salary+placement) via fuzzy header matching and a custom mapping.yaml, records unmapped columns, enforces the provenance contract | 11 | test_phase11_outcomes::test_provided_loader_fixture_1_fuzzy_matching / _2_custom_mapping_yaml | 1 |
| R15 | Working, demoable, deployable system | 1 | Docker + `make demo` + /health/ready | 0,9 | make demo; test_health | 1 |
| R16 | Provider-level outcome data (placement rates and earnings per training provider, not just per trade) | 3 | ProviderOutcome keyed on (centre, course, cohort) with placement_rate + earnings distribution; /providers/{id}/outcomes | 11 | test_phase11_outcomes::test_provider_outcomes_endpoint | 1 |
| R17 | Earnings ranges (p25/median/p75), not single averages | 2 | ProviderOutcome.earnings_p25/median/p75 returned by /outcomes and the grounder FactCards | 11 | test_phase11_outcomes::test_outcomes_api_shape_and_provenance | 1 |
| R18 | Grounded in-language conversational dialogue (free text, not fixed chips) | 3 | Free-text turns (hi/en/hinglish) through the Phase 12 engine; replies carry only DB-grounded facts rendered via FactCard with source/year/demo badge; LLM rephrasing is number-validated | 12,15 | test_phase12_conversation; run_convo_eval.py (124 utterances); ChatPanel.test | 1 |
| R19 | Sentiment shift tracking over time (automatic, per-session trajectory) | 3 | Per-turn automatic sentiment + intensity, Rs snapshot per turn, calculate_shift_label and /resistance/timeseries trend — no manual tap required | 13 | test_phase13_resistance_analytics::test_resistance_timeseries_and_map | 1 |
| R20 | Live human connection with contact details and case pack | 3 | Escalation stores contact_phone/preferred_language/preferred_slot/channel/priority + case_pack_json (last turns, topics, latest Rs, shortlisted trades with grounded facts, family context incl. income_band); counsellor claim/contact/resolve/notes into the thread | 14 | test_phase14_escalation (case-pack contents, lifecycle) | 1 |

## Phase 18 audit

`python scripts/ps_audit.py` → **~98.25%** — **PASSES the 0.97 gate**, and every
status-1 row above carries a named test/e2e/script artefact (the audit fails any
complete row without evidence).

**The one honest remaining partial (R7 = 0.5):** household **income_band** is
captured at intake and is carried into the escalation case pack, but it does not
yet *tailor* the answers or the recommendation ranking the way location and
academic background do. This is a known, deliberate gap, not an untested feature,
and is called out in `docs/ASSUMPTIONS.md` and `docs/EVAL_REPORT.md`.

### What is solid and kept from the earlier phases
- Adaptive assessment engine (RIASEC + aptitude, eval-gated)
- Hybrid recommender with reason codes, explainability and a vocational filter
- Rules-based eligibility (never ML for hard constraints)
- Family Room (weights, votes, consensus) and guest parent join
- Source / year / is_demo provenance on every reference row
- Privacy-preserving small-group suppression (k<5) and the audit log
- Role-based access, en+hi parity, Docker, CI
- Outcome backbone with provider-level earnings ranges, placement, schemes,
  progression (Phase 11)
- Grounded multi-lingual conversation engine with number validator (Phases 12, 15)
- Automatic sentiment + resistance-shift analytics (Phase 13)
- Live human escalation with contact details and case pack (Phase 14)
- Scheme-admin resistance dashboard v2 (Phase 16)
- Low-literacy + low-bandwidth evidence pack (Phase 17)
- Conversation eval on 124 utterances + this final honest audit (Phase 18)

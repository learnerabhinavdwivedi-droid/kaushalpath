# 01 — PS Analysis (practicality, hackathon-expert view)

## 1. What the PS most likely asks (VERIFY against PS_SPEC.md)
- Students entering vocational/skill education (ITI, NSQF courses, polytechnic, skill centres) pick trades with little guidance.
- Parents/family often decide, driven by cost, distance, status, job certainty -> need a FAMILY decision-support layer, not only student-side advice.
- Output: AI career counselling + comparison + roadmap that a low-literacy, vernacular, low-bandwidth family can use.

## 2. Practicality verdict
| Area | Verdict | Why |
|---|---|---|
| Software-only | Easy to demo | No hardware risk |
| Data | MEDIUM RISK | Trade/salary/local-demand data is scattered; must use open taxonomies + clearly labelled demo data |
| ML accuracy | MEDIUM RISK | No ground-truth "right career". Must define measurable gates (see 04_EVAL_PLAN) |
| Differentiation | HIGH potential | Most teams build only a RIASEC quiz. Family Decision Room + explainability + vernacular voice is the edge |
| 36h finale feasibility | OK if scope locked | Phases 0-7 are MVP, 8-9 polish |

## 3. What judges score (SIH lens): Innovation, Feasibility, Impact, Architecture, Working demo, Scalability
- Innovation: family-in-the-loop decision engine + explainable reason codes + counsellor override.
- Feasibility: open data, free/low-cost stack, runs offline-first.
- Impact: rural/first-gen learners, vernacular, voice, WhatsApp-share PDF.
- Demo: 4-minute story: student -> assessment -> top-3 -> parent opens Family Room in Hindi -> compare -> roadmap.

## 4. Core modules (MUST)
1. Student profile + adaptive assessment (interests RIASEC, aptitude mini-test, constraints: education level, district, budget, language, willingness to relocate)
2. Hybrid recommender: hard filters -> semantic retrieval -> re-rank -> explanation
3. Family Decision Room: shared room code, roles (student/parent/counsellor), weighted criteria sliders (cost, duration, salary, local jobs, distance), compare table, vote, consensus score
4. Roadmap: course -> training centre -> certification/NSQF level -> placement/apprenticeship
5. Multilingual UI (Hindi + English minimum), accessibility, low-bandwidth PWA
6. Counsellor dashboard (cohort view, override, feedback)
7. Eval harness + accuracy report
8. Privacy/consent (DPDP-style): minimal data, consent screen, delete-my-data

## 5. Nice-to-have (only after MVP)
Voice input (Whisper), WhatsApp share, scheme/loan eligibility hints, local-demand heatmap, offline cache.

## 6. Scope cuts (so you finish)
- No real-time job-portal scraping. Use a versioned CSV/JSON snapshot.
- No custom LLM training. Use pretrained embeddings + LightGBM/weighted scorer.
- LLM only for natural-language explanation text, with deterministic fallback template.

## 7. Top risks and mitigation
| Risk | Mitigation |
|---|---|
| Fake/unsourced salary data | every row has `source`, `year`, `is_demo`; UI shows source badge |
| "95% accuracy" challenged by judge | show eval report: dataset, metric, split, confusion/NDCG, honest limitations |
| LLM hallucination | LLM never picks careers; it only verbalises ranked output; templates fallback |
| Parent can't read English | Hindi first-class, voice read-out, icons |
| Bias (gender/caste/region) | never use caste/religion as features; gender not a feature; run fairness slice report |

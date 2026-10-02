# 03 — Phases (each ends with a GATE; do not skip)
| # | Phase | Output | Gate |
|---|---|---|---|
| 0 | Spec lock + scaffold | PS_SPEC, traceability matrix, repo, Makefile, docker | `make check` green |
| 1 | Data layer | schema, migrations, occupation/course/market loaders | row counts + source on every row |
| 2 | Assessment engine | adaptive RIASEC + aptitude + API | short-vs-full agreement test |
| 3 | Recommendation engine | filter->retrieve->rank->explain | unit tests, 0 eligibility violations |
| 4 | Eval harness (accuracy gate) | gold set, metrics, report | Top-3 hit >= 95%, NDCG@5 >= 0.90 |
| 5 | Backend APIs + Family Room logic | auth, rooms, votes, compare, roadmap | integration tests |
| 6 | Student frontend + i18n | register, assess, results (Hindi/English) | Lighthouse a11y>=90, PWA installable |
| 7 | Family Decision Room UI | weights sliders, compare, vote, roadmap, PDF/share | e2e demo path works |
| 8 | Counsellor dashboard + feedback | cohort, override, analytics | role-based access tests |
| 9 | Hardening + final audit | security, consent, docker, demo script, PS audit | traceability >= 97%, `make eval` passes |

Time plan (if ~6-7 weeks before finale): P0-1: wk1 | P2-4: wk2-3 | P5-7: wk4-5 | P8-9: wk6 | buffer wk7.

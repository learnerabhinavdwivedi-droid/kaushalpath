# KaushalPath — Evaluator Q&A (rev. Phase 18)

20 questions a judge is likely to ask, answered honestly. The recurring theme:
**we are explicit about what is real, what is demo, and what is a rule vs. a
model.**

### 1. Where does the data come real? Is this live?
No. All occupation/course/centre/market rows are **demo data** (`source=demo_synth_2026`,
`is_demo=true`) and wear a yellow **DEMO** badge in the UI. The PS itself ships no
dataset ("NA — dummy placement/earnings datasets to be provided at evaluation"). We
built the ingestion path to the *verified-data schema*, so the real MSDE file drops
into `backend/app/data/raw/provided/` and loads with **zero code change** (`make seed`).

### 2. So what have you actually *proven*?
That the **system** works end-to-end and is honest: 0 % eligibility violations,
explainable recommendations, the family decision loop, the counsellor dashboard, a
deployable hardened stack, and a reproducible eval harness (`make eval-final`) and PS
audit (`make ps-audit`). We prove **capability + integrity**, not real-world accuracy.

### 3. How do you define "accuracy"? Why not top-1?
There is no single "correct career", so top-1 is noise. We measure **G1** hard-rule
compliance (must be 0), **G2** top-3 hit-rate against a rubric-graded gold set,
**G3** NDCG@5 ranking quality, **G5** explanation coverage, **G6** urban/rural fairness,
**G7** latency. Full definitions in `docs/04_EVAL_PLAN.md`, results in `docs/EVAL_REPORT.md`.

### 4. Your gold labels — who validated them?
Honestly: **we did not run a human expert panel.** The 300 personas are rule-generated
and graded by a written rubric; `eval/gold/human_review.csv` is a *template* with the
`human_label` column empty. We therefore report **no Cohen's κ** and make no
"expert-validated" claim. Numbers show an internally-consistent pipeline.

### 5. Why are some gates 100 % / 0 % — suspiciously perfect?
**G1 = 0** is by construction: the ranker only ever sees courses that already passed a
deterministic eligibility filter, so it *cannot* recommend something ineligible —
that is the design, not luck. **G2 = 100 %** is measured over personas that have a
viable ≥2-grade match (~80 %); we report the other ~20 % as a **catalogue-coverage
gap**, not hide it (see Q7).

### 6. Rules or ML — where's the line?
Hard eligibility (age, education, NSQF level, budget, district reachability) is
**rules, never ML** — non-negotiable. ML (embedding retrieval + LambdaRank re-rank)
only orders within the eligible set. The served demo defaults to a **deterministic
weighted scorer** (transparent, offline) so results are reproducible.

### 7. What's the biggest honest limitation?
**Coverage.** ~20 % of personas (tight budget + cannot relocate + low prior education)
have no eligible course graded ≥2 in a 100-course demo catalogue. The fix is **data**
(more real courses/rural centres), not model tuning. We surface the number rather than
inflate it.

### 8. Where does the LLM sit, and can it hallucinate a career — or a number?
The LLM **only verbalises** already-ranked, non-identifying output (reason codes +
templated data) — it never *chooses* careers. In the conversation engine every
reply is passed through a **numeric-grounding validator**: any figure it tries to
say must exist in the grounded provider/district facts, otherwise the reply is
rejected and the deterministic template is used instead. The eval proves it —
**numeric faithfulness = 1.0** and the adversarial "guaranteed 99 % placement"
stub is refused (`eval/reports/convo_latest.md`). Every path has a template
fallback, so the offline demo runs with **no external API** at all.

### 9. How do you avoid bias / sensitive attributes?
Caste, religion and **gender are never collected or used** as inputs, features,
segments or slices — a codebase-wide search finds zero references. That absence *is*
the control. Fairness (G6) is therefore measured on **urban vs rural**, the only axis
computable without storing a protected attribute.

### 10. Privacy / DPDP?
Consent is required server-side at registration; `DELETE /auth/students/me` performs
real erasure and — because SQLite does **not** enforce FK cascades — the endpoint
*explicitly* deletes the whole conversational trail (the student's conversations,
turns, resistance snapshots and escalations) before the account, verified by
`test_phase18_delete_cascade`; the audit row keeps only **non-identifying counts**,
never the payload. Only coarse district (no GPS, no govt IDs, no phone); small
groups (<5) are suppressed on every dashboard; data minimisation by design.
Details: `docs/PRIVACY.md`.

### 11. Security — what did you actually check?
SQLi (SQLAlchemy expression language only), XSS (no `dangerouslySetInnerHTML`),
JWT algorithm pinned to HS256 with expiry + refresh rotation, rate limiting, secrets
via env only, **prod fail-fast config guards**, security headers, non-root containers,
and a dependency audit (`make security`). Full write-up + real advisory lists:
`docs/SECURITY.md`. Two direct advisories were patched this phase.

### 12. "~98 % PS alignment" — did you just grade yourself generously?
`make ps-audit` recomputes a **weighted** score from `PS_TRACEABILITY.md` and *fails*
any row marked complete that has no evidence (a test, eval gate, or demo artefact).
We did **not** round up to 100 %: one row (**R7 household-income-bracket tailoring**)
is kept honestly at **0.5** because `income_band` is captured and carried into the
escalation case pack but does **not** yet tailor the answer or the ranking — we say
so rather than claim it. Low-literacy (R12) was likewise only upgraded to 1 once a
**real automated axe colour-contrast test** existed, not before. Limitations stay on
the page.

### 13. Scalability — will this survive real load?
Stateless API + JWT (scales horizontally behind Nginx), read-heavy catalogue
(FAISS index + caching), sub-10 ms `/recommend` in eval. SQLite is a **single-node
demo choice**; the app is SQLAlchemy so moving to Postgres is a driver + `DATABASE_URL`
change, no code change. Rate limiting and connection pooling are in place.

### 14. Low-literacy / vernacular — concretely?
Full **Hindi + English** across every screen (i18n parity enforced by
`check-i18n.js`), **read-aloud** on assessment/recommendation text, large touch
targets, low-jargon templated explanations, and a plain-language consent screen.
Accessibility is backed by an automated axe test in CI.

### 15. How is this different from existing govt career portals?
Existing portals are **learner-only, one-way listings**. KaushalPath's unit is the
**family**: a shared decision room where parents adjust weights, see *where* they
disagree, get objection-level answers with local data, vote to consensus, and can
escalate to a human counsellor — plus an admin view of *where resistance concentrates*.

### 16. How reproducible is a demo on a judge's laptop?
`make demo` migrates, seeds, and serves; or `docker compose -f docker-compose.prod.yml
up --build` + the `demo` seed profile. It is **offline-safe**: no model download, no
external keys, deterministic scorer, and the loaders no-op gracefully without raw data.

### 17. What did you add that wasn't strictly asked (scope discipline)?
Deliberately little: an append-only audit trail, an automated a11y test, and prod
hardening — all directly serving a PS requirement or the "demo-proof, judge-proof"
brief. We did **not** add a chart library, a database server, or an LLM dependency.

### 18. Where are the tests and how long is CI?
`make check` runs ruff + mypy + pytest (**109 backend tests**) + vitest (+ axe) +
`check-i18n` + build. The conversation engine and the erasure cascade each have
dedicated Phase-18 tests/evals. The locked **test split is frozen** so final metrics
can't drift.

### 19. What breaks first in real production?
Data quality and counsellor capacity, not code — which is exactly what the dashboard,
escalation queue, and small-group suppression are built to manage. The recommender is
only as good as the verified outcome data MSDE provides; our schema is ready for it.

### 20. If you had two more weeks?
(1) Ingest real NCVI/ITCA course + centre data to close the 20 % coverage gap;
(2) run a genuine expert-labeling pass for the gold set and report κ;
(3) a real Lighthouse/AT accessibility audit for a WCAG-AA claim; (4) Postgres +
managed object storage for outcome documents.

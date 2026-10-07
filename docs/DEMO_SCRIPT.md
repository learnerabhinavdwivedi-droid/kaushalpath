# KaushalPath — 4-Minute Demo Script (rev. Phase 18)

A tight, judge-facing walk-through. Rehearse once end-to-end. Every talking
point maps to a PS 26241 requirement so the evaluator hears coverage, not just
features. **If anything can fail live, pre-run it and keep the API/`curl` output
in a second tab as a fallback.**

## Before you present (2 min setup)

```bash
make demo            # migrates + seeds the catalogue + serves API on :8000
# second shell:
npm --prefix frontend run dev     # http://localhost:5173
```
Pre-open: the app, `/docs` (dev), a terminal with `curl localhost:8000/health/ready`,
and `docs/PS_TRACEABILITY.md` + `docs/EVAL_REPORT.md` in tabs. Or run the whole
stack in prod mode: `docker compose -f docker-compose.prod.yml up --build` then
`docker compose -f docker-compose.prod.yml --profile demo run --rm seed`, open
`http://localhost`.

> Honest framing to say out loud early: salaries/placement in this build are
> **demo data** — every number wears a yellow `DEMO` badge. Real MSDE outcome
> data drops into `data/raw/provided/` and ingests with **zero code change**.

## Beat sheet (240 s) — the spine is one family's objection, start to finish

### 0:00–0:20 — The problem (R1, R2)
> "Government career counselling in India is one counsellor to thousands of
> students, and the *real* decision is made at home by a family that has to
> trust it. KaushalPath counsels the **learner and the family together**, in
> their language — and when words aren't enough, it hands off to a human." Show
> the landing page; toggle **EN / हिन्दी** top-right.

### 0:20–0:55 — Learner onboarding + explainable recommendation (R7, R11, R12, R13)
1. **Register** a student → point at the **consent screen** (required server-side,
   plain Hindi+English; delete-anytime right — PRIVACY.md).
2. **Profile** (district, education, budget, **household income band**) →
   **adaptive assessment** stops by **≤ 24 items** (G4). Hit the **read-aloud (🔊)**
   button once — "low-literacy users can hear every item" (R12, axe-tested).
3. **Results**: three careers, each with **reason codes** + a **yellow `DEMO`
   source badge** on every number — "not a black box" (R13). Click one → **roadmap**
   (qualification → centre → cert → job, NSQF progression, earnings + placement).

### 0:55–2:25 — Family Room: a Hindi parent objects, and the system answers with data (R1, R2, R18) — the centrepiece
1. **Create a room** → share the **code**. In an incognito tab, **join as a parent
   in हिन्दी** (no account needed for a guest parent — R1).
2. Open the **conversation (/talk)** and type the objection *as a hesitant Hindi
   parent* (e.g. "पहले महीने में कितनी कमाई होगी? नौकरी पक्की?"). Point out: it is
   **free text, not fixed chips**, and the reply comes back **in Hindi**.
3. The engine classifies the concern (income / job-security) and grounds the answer
   in **provider + district outcome facts** — **median / p25 / p75 earnings,
   placement rate, fee** — rendered as **FactCards with a source + year + `DEMO`
   badge**. Say: "it can only say numbers that exist in the database — it *refuses*
   to invent one" (numeric-faithfulness eval = **1.0**, `convo_latest.md`).
4. Ask a second, sharper objection. Point at the **resistance (Rs) meter**: sentiment
   + intensity are tracked **per turn** and Rs **rises** as the parent hardens (R9,
   R19). Then a grounded answer softens it — show the **shift** (hardened →
   softened).
5. When it can't fully satisfy them, click **one-tap "talk to a counsellor"** →
   **escalate** (R8). Show the **case pack**: last turns, topics, latest Rs,
   shortlisted trades with their grounded facts, family context (incl. income band).

### 2:25–2:55 — The human takes over (R8, R20)
Log in as a **counsellor**: the escalation is already **auto-routed to the
least-loaded** cohort counsellor. **Claim** it (atomic — a second tab can't
steal it), walk the lifecycle **open → assigned → contacted → resolved**, and
reply into the family's thread. "Unresolved cases go to a *person*, not a dead
end."

### 2:55–3:35 — Admin: where resistance concentrates (R9, R10)
Open **/admin/resistance** (the scheme-admin dashboard): KPI strip, an **offline
district bubble map**, a **concern × trade heat matrix**, a 30-day **trend**, and
the **shift bars** (how many families softened vs hardened) — all fed by the
conversation we just had. **Say**: "any bucket backed by fewer than 5 students is
suppressed — we won't expose an individual" (privacy).

### 3:35–4:00 — Hardening & honesty close (deploy-proof, judge-proof)
Fast, confident:
- `curl localhost:8000/health/ready` → `{"status":"ready","db":"up"}` — plus
  security headers, rate-limited JWT auth, non-root prod containers.
- Open **EVAL_REPORT.md**: "Recommendation gates all pass — **0 % eligibility
  violations**, top-3 hit-rate 100 %, NDCG 0.93 — **and** the conversation engine
  is separately eval'd: 124 utterances, topic accuracy 0.92, **numeric faithfulness
  1.0**, escalation recall 1.0. Here are the limits we did NOT hide: synthetic
  utterances, demo outcome data, lexicon sentiment."
- Open **PS_TRACEABILITY.md** + run **`make ps-audit`**: "**~98 % weighted PS
  alignment**, every 'done' row links to a test or artefact, and one row
  (**income-bracket tailoring**) stays honestly at 0.5 because we don't fake it."
> "It's built, it's honest, and it deploys with one command. Thank you."

## Fallback one-liners (if the UI is being fussy)
```bash
python scripts/demo_flow.py         # API-only: register→room→vote→consensus
curl -s localhost:8000/health/ready
make eval-final                     # reprint the recommendation gate table
python eval/scripts/run_convo_eval.py  # reprint conversation-engine metrics
make ps-audit                       # reprint alignment score
```

## Demo-data checklist (do NOT ship unmarked)
- [ ] Every earnings/placement figure shows the yellow `DEMO` badge.
- [ ] Consent screen visible in both EN and HI.
- [ ] Small-group suppression line present on the resistance dashboard.
- [ ] Limitations stated aloud, not skipped.

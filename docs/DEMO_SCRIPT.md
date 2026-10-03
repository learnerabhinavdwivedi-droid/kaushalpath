# KaushalPath — 4-Minute Demo Script (Phase 9)

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

## Beat sheet (240 s)

### 0:00–0:20 — The problem (R1, R2)
> "Government career counselling in India is one counsellor to thousands of
> students, and the *real* decision is made at home by a family that has to
> trust it. KaushalPath counsels the **learner and the family together**, in
> their language." Show the landing page; toggle **EN / हिन्दी** top-right.

### 0:20–1:05 — Learner onboarding (R7, R11, R12, + privacy)
1. **Register** a student → point at the **consent screen** ("we store your
   profile to recommend; you can delete anytime") — say: consent is **required
   server-side**, plain Hindi+English (PRIVACY.md).
2. **Profile / constraints** — district, education, budget, **household income
   band**, relocate yes/no. Note: family context shapes the *explanation*, never
   the aptitude score.
3. **Adaptive assessment** — answer a handful of RIASEC + aptitude items. Say:
   the engine stops by **≤ 24 items** with a reliable profile (G4), not a fixed
   72-question test. Switch the UI to **Hindi** mid-assessment.
4. Click the **read-aloud (🔊)** button on a question — "low-literacy and
   low-digital-familiarity users can hear every item" (R12, axe-tested).

### 1:05–1:40 — Explainable recommendations (R3, R6, R13)
On **Results**, open a career card and narrate:
> "This is **not** a black box. Three careers, each with **reason codes** —
> why it matched — and a **source badge** on every number." Point at a reason
> chip ("matches your Realistic profile", "high local demand"), then the yellow
> `DEMO` source tag. **Click into a career** → Roadmap.

### 1:40–2:05 — The roadmap (R5)
On the **career detail / roadmap**: qualification → **centre** → certification →
job, with **NSQF level progression**, average **earnings** and **placement rate**
(demo-badged). "A concrete path, not just a job title."

### 2:05–2:55 — Family Decision Room (R1, R2, R8) — the centrepiece
1. **Create a room** → get the share **code**.
2. In an incognito tab, **register a parent (Hindi)** and **join by code**.
3. Parent **adjusts criterion weights** (salary↑, safety↑) — show recommendations
   re-rank live for the family's priorities.
4. Open **Compare** → "the system surfaces **where the family disagrees**" —
   highlight the disagreement on a criterion.
5. Answer a **parental objection** (income / job security / social perception)
   with the tap-to-ask Q&A — "credible local data, in the parent's language".
6. Both **vote** → **Consensus** view shows the agreement score.
7. Click **Escalate to a counsellor** — "unresolved cases go to a *human*, not a
   dead end" (R8).

### 2:55–3:35 — Counsellor + admin view (R8, R9, R10)
Log in as a **counsellor** (or show `/counsellor`):
> "This is where the scale problem gets solved." Show:
- **Cohort** queue incl. the **open escalation** from the family just now.
- **Analytics** — RIASEC distribution, top trades, district demand view.
- **Resistance dashboard** — *where* and *why* families push back, by topic ×
  district × trade. **Say**: "any bucket backed by fewer than 5 students is
  suppressed — we won't expose an individual" (R10 + privacy).
- **Audit** tab — overrides and deletions are logged (append-only).

### 3:35–4:00 — Hardening & honesty close (deploy-proof, judge-proof)
Fast, confident:
- `curl localhost:8000/health/ready` → `{"status":"ready","db":"up"}` — plus
  security headers, rate-limited JWT auth, non-root prod containers.
- Open **EVAL_REPORT.md**: "All gates pass — **0 % eligibility violations**,
  top-3 hit-rate 100 %, NDCG 0.93, p95 single-digit ms — **and here are the
  limitations we did NOT hide**: synthetic personas, demo data, 80 % catalogue
  coverage."
- Open **PS_TRACEABILITY.md**: "**100 % of PS requirements are implemented with
  a test or artefact behind each** — `make ps-audit` proves it, reproducibly."
> "It's built, it's honest, and it deploys with one command. Thank you."

## Fallback one-liners (if the UI is being fussy)
```bash
python scripts/demo_flow.py         # API-only: register→room→vote→consensus
curl -s localhost:8000/health/ready
make eval-final                     # reprint the gate table
make ps-audit                       # reprint alignment score
```

## Demo-data checklist (do NOT ship unmarked)
- [ ] Every earnings/placement figure shows the yellow `DEMO` badge.
- [ ] Consent screen visible in both EN and HI.
- [ ] Small-group suppression line present on the resistance dashboard.
- [ ] Limitations stated aloud, not skipped.

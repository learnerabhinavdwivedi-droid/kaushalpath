# KaushalPath

AI-enabled **career counselling + family decision-support** platform for vocational
education (ITI / NSQF / polytechnic). Smart India Hackathon 2026 — **PSID 26241**.

A student completes an adaptive interest + aptitude assessment and enters constraints;
the system recommends top-3 vocational careers/courses **with explainable reason codes**.
A parent joins a shared **Family Decision Room** (Hindi/English), adjusts criteria weights,
compares options, votes, and gets a roadmap (course → centre → certification → job).
Counsellors see a cohort dashboard.

> **Status: Phase 0 (skeleton).** FastAPI `/health` + request-id middleware, React/Vite
> placeholder with i18n (en/hi), Docker, Makefile, CI and smoke tests are in place.
> Data, assessment, recommender, Family Room, eval harness and dashboards land in Phases 1-9.

## ⚠️ Before anything else
Paste the **official** PSID 26241 brief into [`docs/PS_SPEC.md`](docs/PS_SPEC.md). It is
currently an unverified working title (see [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) A1),
and it overrides all other docs on conflict.

## Layout
```
backend/   FastAPI app (app/main.py), core config+logging, tests
frontend/  React 18 + Vite + TS + Tailwind + react-i18next
docs/      PS analysis, architecture, phases, eval plan, traceability matrix
prompts/   00_MASTER_CONTEXT + PHASE_0..9 (one prompt per coding session)
eval/      gold personas, eval scripts + reports (Phase 4)
scripts/   data loaders (Phase 1)
```

## Run locally
```bash
cp .env.example .env          # then edit values
make install                  # python venv + npm install
make dev                      # uvicorn on :8000 (frontend: npm --prefix frontend run dev)
make check                    # lint + tests (backend + frontend)
docker compose up             # full stack
```

## Key rules (see [`RULES.md`](RULES.md) / [`AGENTS.md`](AGENTS.md))
- Hard eligibility/age/NSQF/budget constraints are **rules, never ML** — 0% violations.
- Every recommendation returns **reason codes + data source**; no black box.
- No fabricated data as real: every row carries `source`, `year`, `is_demo`.
- LLMs only verbalise ranked output; they never choose careers.
- Accuracy claims come **only** from `make eval`. Never use caste/religion/gender as features.

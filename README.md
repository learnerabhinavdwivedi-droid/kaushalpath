# KaushalPath

**AI-enabled career counselling + family decision-support for vocational
education** (ITI / NSQF / polytechnic). Smart India Hackathon 2026 — **PSID 26241**
(MSDE · Smart Education).

KaushalPath does not just recommend a career to a student — it brings the **whole
family** into a shared, vernacular decision. A learner completes an adaptive
interest + aptitude assessment and enters constraints; the system recommends the
top vocational careers/courses **with explainable reason codes** (never a black
box). A parent joins a shared **Family Decision Room** (Hindi / English), adjusts
what matters to them, sees *where* the family disagrees, answers objections with
credible local data, votes to consensus, and gets a roadmap
(course → centre → certification → job). Counsellors see a cohort dashboard and
*where family resistance concentrates* — with privacy-preserving aggregation.

## Status: complete (Phase 9 — hardened, deployable, audited)

All nine phases shipped. `make check` green (63 backend + frontend tests, incl. an
automated accessibility audit), `make eval-final` meets every gate, and
`make ps-audit` scores **100 %** PS alignment with evidence behind every row.
Honest limitations (demo data, synthetic personas, catalogue coverage) are stated,
not hidden.

## The non-negotiables (what makes it trustworthy)

- **Hard eligibility is rules, never ML** — the recommender *cannot* return a
  course a student isn't eligible for (age / education / NSQF / budget / district).
- **Every recommendation returns reason codes + a data source** — explainable by design.
- **No fabricated data presented as real** — every row carries `source` / `year` /
  `is_demo`; demo figures wear a visible badge.
- **LLMs only *verbalise* ranked output** — they never choose careers; every path has
  a deterministic, offline fallback.
- **Accuracy claims come only from `make eval`** — and we never lower a threshold to pass.
- **Caste, religion and gender are never collected or used** as features or slices.

## Architecture

FastAPI (Pydantic v2, SQLAlchemy 2 + Alembic, SQLite dev) · ML stack
sentence-transformers + FAISS retrieval, LightGBM LambdaRank re-rank, deterministic
RIASEC + aptitude assessment · React 18 + Vite + TS + Tailwind + Zustand +
react-i18next PWA · Docker + Nginx · pytest / vitest / ruff / mypy.

```
backend/    FastAPI app: routes, services, ML (assessment/retrieval/ranking/explain), models
frontend/   React SPA/PWA: assessment, results, Family Room, counsellor dashboard, i18n (en/hi)
scripts/    data loaders, seed pipeline, backup, demo flow, PS audit
eval/       gold personas + rubric labels, eval runner + reports
docs/       PS spec/analysis, architecture, phases, eval plan, traceability,
            SECURITY, PRIVACY, EVAL_REPORT, DEMO_SCRIPT, QA_ANSWERS, ASSUMPTIONS
infra/      CI workflow, production Nginx config, prod env template
prompts/    00_MASTER_CONTEXT + PHASE_0..9 (one prompt per build session)
```

See [`docs/02_ARCHITECTURE.md`](docs/02_ARCHITECTURE.md) for the full design and
[`docs/PS_TRACEABILITY.md`](docs/PS_TRACEABILITY.md) for requirement→evidence mapping.

## Run it

**One-command demo** (migrates, seeds the catalogue, serves the API — offline-safe,
no external API/model download):

```bash
cp .env.example .env         # edit values (dev defaults work as-is)
make install                 # python venv + npm install
make demo                    # alembic upgrade head + seed + uvicorn on :8000
# in a second shell:
npm --prefix frontend run dev            # http://localhost:5173
```

**Full stack in production mode** (hardened, single-origin behind Nginx):

```bash
cp infra/env.prod.example .env           # set a real SECRET_KEY etc.
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml --profile demo run --rm seed   # load demo data
# open http://localhost
```

> On Windows, run the `make` targets from Git Bash / WSL, or invoke the underlying
> commands directly (they're one-liners in the [`Makefile`](Makefile)).

## Verify it

```bash
make check        # lint (ruff) + types (mypy) + tests (pytest 63 + vitest) + i18n + build
make eval-final   # locked test split -> docs/EVAL_REPORT.md numbers
make ps-audit     # weighted PS alignment score (fails a "done" row with no evidence)
make security     # pip-audit (backend) + npm audit (frontend) -> docs/SECURITY.md
make backup       # consistent SQLite snapshot -> backups/
```

## Documentation

| Doc | What it answers |
|---|---|
| [`docs/PS_SPEC.md`](docs/PS_SPEC.md) / [`docs/PS_TRACEABILITY.md`](docs/PS_TRACEABILITY.md) | The official brief, and how each requirement is met (+ evidence) |
| [`docs/EVAL_REPORT.md`](docs/EVAL_REPORT.md) | How we measure accuracy, and the honest limits |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, controls, and real dependency-audit output |
| [`docs/PRIVACY.md`](docs/PRIVACY.md) | DPDP-aligned data handling, consent, deletion |
| [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) | The 4-minute walk-through |
| [`docs/QA_ANSWERS.md`](docs/QA_ANSWERS.md) | 20 evaluator questions, answered |
| [`docs/ASSUMPTIONS.md`](docs/ASSUMPTIONS.md) | Every ambiguity and how we resolved it |

## Key rules

See [`RULES.md`](RULES.md) / [`AGENTS.md`](AGENTS.md). The six non-negotiables above
are enforced in code, tests and the eval harness — not just in this README.

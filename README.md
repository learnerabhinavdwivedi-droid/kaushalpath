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

## Frontend: app routes + SparkLab marketing landing

The frontend hosts two UIs side by side on one Vite/React/TS + Tailwind build:

| Route | What it is |
|---|---|
| `/` | KaushalPath app (landing, assessment, results, counsellor dashboards) |
| `/home` | SparkLab-style marketing landing (the animated showpiece page) |
| `/styleguide` | Design-system page: tokens + UI primitives |

```bash
npm --prefix frontend run dev        # dev server on :5173
npm --prefix frontend run build      # tsc --noEmit + vite build (type + prod gate)
npm --prefix frontend test           # vitest: app tests + axe-core a11y audits
npm --prefix frontend run test:e2e   # Playwright (responsive + flow specs)
```

### Editing the landing-page copy — no component changes needed

All marketing text and data lives in **one file**: `frontend/src/content/site.ts`.

- `nav`, `hero`, `courses`, `projects`, `schedule`, `howItWorks`, `about`,
  `testimonials`, `faq`, `cta`, `marquee`, `footer` — sections render straight from it.
- Add a course: append an object to `courses` (`variant`/`pillStyle` pick the colour
  scheme, `mascot` picks the SVG from `sections/CoursesArt.tsx`, `span: 2` makes it wide).
- Never hardcode strings in components; the i18n dictionaries (`src/i18n/en|hi.json`)
  stay in charge of the app UI, `site.ts` of the marketing site.
- Images are placeholder art by design (rounded blob mascots + gradient blocks, rule:
  no copied assets). Swap them by dropping files into `frontend/public/illustrations/`
  and passing `src` to `components/ui/SmartImage.tsx` — lazy-loading, shimmer skeleton
  and blur-up are already wired; pass `width`/`height` to avoid layout shift.

### Animation + accessibility conventions (enforced)

- Motion tokens live in `src/lib/motion.ts` (`SPRING`, `DURATION`, `EASE`); shared
  interaction hooks in `src/hooks/interactions.ts` (`useTilt`, `useSpotlight`,
  `useMagnetic`, `useReveal`, `useCanHover`).
- Only `transform` / `opacity` / `clip-path` animate. `MotionConfig reducedMotion="user"`
  in `components/layout/Layout.tsx` degrades every Framer animation for OS-level
  reduced-motion; CSS animations have their own `@media (prefers-reduced-motion)` guards.
- Scroll reveals are lighter on mobile (opacity-only, no stagger) via `useReveal`.
- Desktop custom cursor is opt-out: toggle button bottom-right, disabled automatically
  for touch and reduced-motion users.
- `src/marketing-a11y.test.tsx` runs **axe-core** over the whole landing page in CI
  (zero violations) and asserts one `h1`, `h2` section headings, skip link + `main`
  landmark and accessible names on icon-only controls. `color-contrast` is the one
  excluded rule (jsdom has no layout engine): ink `#0A0A0A` / muted `#55554A` on page
  `#F1F5E0` ≈ 6.4:1 and white on green `#0F7B3F` ≈ 5.4:1 pass AA. White on the pure
  accent orange `#FF4F00` is only ≈ 3.3:1, so any surface carrying white body text uses
  the AA-safe `orange-deep` `#C13A00` token (≈ 5.4:1); `orange` stays for accents, icons
  and dark-on-orange fills.

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

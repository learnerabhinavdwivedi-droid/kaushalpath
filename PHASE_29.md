# PHASE 29 — Demo focus, scope trim, and judge Q&A hardening

**Priority:** P1
**Effort:** 0.5–1 day
**PS rows touched:** none directly — this protects how clearly the existing rows are *shown*

## Why this phase exists

The PS differentiator is explicitly the family unit + vernacular conversational UI + admin
resistance dashboard, not the recommender's ML sophistication or the marketing landing page.
The repo currently also hosts a separate "SparkLab"-style marketing site at `/home`, a custom
cursor, scroll-reveal animation system, and a style-guide page — all fine as portfolio polish,
but none of it is what the PS is scored on, and a tight demo window is the wrong place to let it
compete for attention. Combined with the honest answers Phase 25 and 28 now give you, this phase
makes sure the live walkthrough and the Q&A are both airtight.

## Prompt

PHASE 29 — DEMO FOCUS + Q&A HARDENING.

1. Audit `frontend/src/pages` routes. Confirm `/home` (SparkLab marketing landing),
   `/styleguide`, and any other non-PS routes are not linked from the primary navigation shown
   during judging. Do not delete them — they're legitimate engineering polish — just make sure
   `docs/DEMO_SCRIPT.md`'s walkthrough never touches them.
2. Rewrite `docs/DEMO_SCRIPT.md` tightly around this sequence, with a timed budget per beat
   summing to under 4 minutes: adaptive assessment → Family Room, parent joins by room code →
   Hindi-language parental objection typed or spoken → grounded FactCard reply with
   source/year/is_demo badge → resistance score visibly shifts → escalation triggered, case
   pack built → counsellor claims it from the pool → admin dashboard shows the district/concern
   heat matrix updating live.
3. Update `docs/QA_ANSWERS.md` with sharp, rehearsed answers to the two hardest questions this
   audit surfaced: "Walk me through how your expert validation data was collected" (answer
   honestly — simulated, methods note at `eval/gold/METHODS.md`, real pilot data attached if the
   Phase 25 stretch goal was completed) and "What happens on evaluation day when you're handed
   the real MSDE dataset?" (point straight at `docs/MSDE_DAY_RUNBOOK.md` from Phase 28, and state
   the measured ingestion time).
4. Do one fresh-clone dry run exactly as a judge's laptop would encounter it: clone the repo to
   a clean directory, run `make install && make demo`, open two separate browser profiles
   (parent + learner) with no prior local state, and complete the full script from step 2 while
   timing it. Fix anything that breaks or feels slow.

## Gate (acceptance)

- `docs/DEMO_SCRIPT.md` has per-beat timings that sum to under 4 minutes.
- `docs/QA_ANSWERS.md` contains honest, specific answers to both questions in step 3, each
  pointing at a real artefact in the repo (not a vague reassurance).
- The fresh-clone dry run from step 4 is completed and logged with a timestamp and total time in
  `docs/ASSUMPTIONS.md`.

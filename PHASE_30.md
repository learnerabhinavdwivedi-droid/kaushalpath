# PHASE 30 — Final pre-submission verification lock

**Priority:** P0 (always run last)
**Effort:** 2–3 hours
**PS rows touched:** all — this is the final honest re-score, not a new capability

## Why this phase exists

Phases 25–29 changed scoring code, data labeling, and docs. Before anything is said out loud on
stage, every number that will be quoted needs to be reproducible on command, right now, on the
actual current state of the repo — not remembered from an earlier run.

## Prompt

PHASE 30 — FINAL VERIFICATION LOCK.

1. Run, in this order, and paste the real (not remembered or hand-typed) terminal output into a
   new dated entry in a "Changelog" section at the bottom of `docs/EVAL_REPORT.md`:
   `make check`, `make eval-final`, `make ps-audit`, `make security`,
   `python scripts/demo_preflight.py` (Phase 27), `python scripts/data_provenance_audit.py`
   (Phase 25).
2. Re-generate `docs/PS_TRACEABILITY.md`'s final weighted score with the updated R2, R7, R9, R14
   rows from Phases 25/26/28. Confirm `make ps-audit` still enforces that no row marked `1` lacks
   a currently-passing, named test — treat any failure here as a submission blocker, not a
   formatting nit.
3. Add a `CHANGELOG.md` entry summarizing exactly what changed since Phase 18: eval-report
   relabeling and de-circularized expert gold (25), income-band tailoring (26), LLM-fallback
   hardening (27), MSDE ingestion drill (28), demo/Q&A hardening (29) — dated, so judges who
   read repository history see honest, incremental progress rather than one unexplained
   monolithic commit right before the deadline.
4. Tag the commit, e.g. `git tag sih2026-submission`, so there is one unambiguous, citable
   snapshot you can point a judge to if asked "which commit is the one you're presenting."

## Gate (acceptance)

- Every command in step 1 exits 0, with its real output pasted into `docs/EVAL_REPORT.md`.
- `docs/PS_TRACEABILITY.md`'s computed score reflects the Phase 25/26/28 changes with every
  status-`1` row evidenced.
- `CHANGELOG.md` is committed and the `sih2026-submission` git tag exists.

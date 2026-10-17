# PHASE 28 — MSDE dummy-dataset ingestion drill

**Priority:** P0
**Effort:** 1 day
**PS rows touched:** R14 (uses the datasets provided)

## Why this phase exists

The official PS text is explicit: "Dataset Link — NA — dummy placement/earnings datasets to be
provided for hackathon evaluation." That means on evaluation day you will be handed a file in a
shape you have never seen, live, with everyone watching, and you need `load_provided_dataset.py`
to ingest it correctly with zero code changes — only `mapping.yaml` edits are allowed per
`docs/PS_SPEC.md`'s own plan. Right now that loader has only ever been exercised against your
own fixture. Stress-test it against formats you have deliberately not seen before, while you
still have time to fix what breaks.

## Prompt

PHASE 28 — MSDE INGESTION DRILL.

1. Hand-construct 2–3 deliberately "unfamiliar-shaped" dummy placement/earnings files and place
   them as fixtures in `backend/tests/fixtures/msde_dummy_variants/`: vary column order, add
   extra unexpected columns the loader has never seen, drop an optional column, mix units
   (e.g. annual vs monthly earnings in different files), and use a different date format than
   your existing fixture.
2. Run `load_provided_dataset.py` against each variant via `make seed`, using only edits to
   `mapping.yaml` — no `.py` changes allowed in this step, to simulate the real constraint on
   eval day. Record exactly how much manual mapping effort each variant required as a new
   "A-MSDE-DRILL" entry in `docs/ASSUMPTIONS.md`.
3. Harden the fuzzy header matcher in `load_provided_dataset.py` to log every column it could
   not map instead of silently dropping it, and surface the unmapped-column count in
   `scripts/data_report.py` so you can sanity-check the real file live in under two minutes.
4. Add `backend/tests/integration/test_phase28_msde_ingestion.py` asserting that rows ingested
   from each fixture variant carry `is_demo=false`, correct `source`/`year`, and pass the same
   provenance-contract test already used for the demo loader (`test_provided_loader_fixture_*`
   in `test_phase11_outcomes.py` — mirror that contract here).
5. Write `docs/MSDE_DAY_RUNBOOK.md`: a one-page, step-by-step script for the moment you're
   handed the real file — exactly where to drop it, which single command to run, how to verify
   row counts, how to spot-check three values against the source file by eye, roughly how long
   the whole thing takes, and what to say to judges if a column can't be auto-mapped (name the
   fallback: it lands in `backend/app/data/raw/provided/`, gets re-run through `make seed`, and
   any unmapped column is reported, not silently dropped).

## Gate (acceptance)

- `make seed` against each of the three fixture variants produces zero unmapped *required*
  columns (optional ones may be logged as unmapped, never silently dropped).
- `pytest backend/tests/integration/test_phase28_msde_ingestion.py` passes for all three
  variants.
- `docs/MSDE_DAY_RUNBOOK.md` exists and has been dry-run once, end to end, with a stopwatch —
  record the actual time taken in the runbook itself.

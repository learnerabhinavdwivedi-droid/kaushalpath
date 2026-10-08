# PHASE 10 — Truth reset and spec lock

**Priority:** P0
**Effort:** 0.5 day
**PS rows fixed:** All (honest baseline)

## Goal

Make the repo honest and clean before building, so the judges' audit and your
own audit agree.

## Prompt

PHASE 10 — TRUTH RESET. Do not add features.

1. Rewrite docs/PS_TRACEABILITY.md. Re-score every row honestly: a row is 1 only if
   code + test + demo evidence exist for the PS wording, not for a nearby feature.
   Set R1, R2, R3, R4, R5, R6, R8, R9, R10, R12, R14 to 0.5 and R7 to 0.5, with a
   one-line reason each. Add R16 provider-level outcomes (W3), R17 earnings ranges
   not single averages (W2), R18 grounded in-language dialogue (W3), R19 sentiment
   shift over time (W3), R20 live human connect with contact + case pack (W3), all 0.

2. Update README status text. Do not claim 100%.

3. git rm backend/kaushalpath.db-journal; add *.db, *.db-journal to .gitignore.

4. Delete frontend/src/i18n/index.ts, en.json, hi.json; make sure only
   i18n/config.ts + locales/*.json are imported; run npm run check-i18n.

5. Refresh backend/app/data/raw/README.md and docs/ASSUMPTIONS.md A1 (resolved).

6. Run make check and make ps-audit. Paste both outputs. Stop.

## Gate

- `make ps-audit` now reports ~60% and FAILS the 0.97 gate. This is expected and correct.
- `make check` is still green. No dead i18n files remain.

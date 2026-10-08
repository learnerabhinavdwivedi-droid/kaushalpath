# PHASE 11 — Outcome-data backbone (trade + provider level)

**Priority:** P0  
**Effort:** 2-3 days  
**PS rows fixed:** R3, R4, R5, R14, R7  

## Goal

Give the system the verified-outcome data the PS actually names: earnings RANGES and placement rates per trade AND per training provider, plus progression pathways, schemes and provider safety facts.

## Prompt

PHASE 11 — OUTCOME DATA BACKBONE. Backend + scripts only. No UI.

Context: today market.csv is per (occupation, state) with one avg_salary_inr and one placement_rate (85 rows, 81 occupations, 19 states). Centres (45) carry NO outcomes. The PS requires verified average earnings, placement rates and progression pathways for specific trades AND training providers.

Do:
A. Alembic migration(s):
   - provider_outcomes(provider_id FK centres.id, course_id FK, cohort_year, enrolled, certified, placed, placement_rate, earnings_p25, earnings_median, earnings_p75, self_employed_pct, apprenticeship_stipend_inr) + SourceMixin.
   - market: add district (nullable), earnings_p25, earnings_p75.
   - centres: add provider_type, affiliation, has_female_trainers, has_hostel, transport_note, safety_certified (provider facts only).
   - progression_paths(from_course_id, to_label, to_course_id nullable, kind in nsqf_levelup|lateral_entry|further_education|apprenticeship, credit_note).
   - schemes(name, benefit_text_en, benefit_text_hi, eligibility_text, url, SourceMixin).
   - occupations: is_vocational bool.
B. Seed CSVs under backend/app/data/seed/ (all is_demo=true, source=demo_synth_2026):
   >= 35 vocational trades, >= 2 providers each, outcomes per provider, progression rows, 6+ schemes (PMKVY, NAPS, etc.). Mark non-vocational occupations is_vocational=false and exclude them from /recommend.
C. Rewrite scripts/load_provided_dataset.py: read backend/app/data/raw/provided/*.csv + mapping.yaml; fuzzy-match headers; normalise INR/percent; write rejected rows to provided_rejects.csv; print unmapped columns. Provided data outranks demo.
D. Add services/outcome_svc.py + GET /outcomes and GET /providers/{id}/outcomes.
E. Tests (2 header-variant fixtures, no-source-no-row, vocational filter, API shape); update scripts/data_report.py. Gate: make check green; paste data_report output.

## Gate (acceptance)

- `scripts/data_report.py` prints coverage per table and per state; every row has source + source_year + is_demo.
- A dropped-in dummy MSDE CSV with unfamiliar headers loads after editing only mapping.yaml (tested with 2 fixture files).
- API: `GET /outcomes?occupation_id&state&district` returns p25/median/p75, placement_rate, n, source, is_demo.
- `make check` is green.

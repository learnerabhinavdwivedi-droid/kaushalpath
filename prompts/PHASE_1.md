# PHASE 1 — Data layer

GOAL: A clean, versioned, source-labelled database of occupations, courses, centres and market data that every later phase reads.

INPUTS: dataset links from docs/PS_SPEC.md (use these FIRST), docs/05_OSS_REPOS.md data sources, docs/02_ARCHITECTURE.md data model.

TASKS:
1. SQLAlchemy models + Alembic initial migration for: users, students, occupations, courses, centres, market, assessments, recommendations, rooms, room_members, criteria_weights, votes, feedback (fields per docs/02_ARCHITECTURE.md). Add indexes on district/state/nsqf_level/occupation_id.
2. backend/app/data/raw/README.md listing each source file, URL, licence, download date (leave a TODO where the user must download manually).
3. Loader scripts in scripts/ (python, idempotent): load_onet.py, load_esco.py (if used), load_provided_dataset.py (PS datasets), build_occupation_master.py (merge to one occupation table with onet_code, esco_uri, nco_code, nsqf_level, name_en, name_hi, description, riasec vector), load_courses.py, load_market.py.
4. Occupation master must include Hindi names (use ESCO/Indic translation or a curated CSV; mark machine-translated ones with `needs_review=true`).
5. Every row stores source, source_year, is_demo. If real India data is unavailable, load clearly marked demo rows from backend/app/data/seed/*.csv and set is_demo=true. UI will later show a "Demo data" badge.
6. A data quality script (scripts/data_report.py) printing: row counts, null %, duplicate %, rows per source, % is_demo, coverage of occupations by NSQF level and by state.
7. Repository functions (no business logic) in backend/app/services/data_repo.py with typed queries: get_occupations(filters), get_courses_for(occupation_id, district), get_market(occupation_id, state).
8. Tests: migration up/down, loader idempotency (run twice, same counts), constraint tests.

ACCEPTANCE: `make seed` then `python scripts/data_report.py` prints counts; at least 150 occupations with RIASEC vectors, every row has a source; `pytest backend/tests/unit -k data` passes.

DO NOT: invent salaries presented as real. Do not scrape sites that forbid it.

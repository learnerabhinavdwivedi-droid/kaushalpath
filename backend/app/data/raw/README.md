# `data/raw/` — source manifest (provenance contract)

Every reference-data row must carry `source`, `source_year` and `is_demo`
(RULES.md). This folder holds the **original downloaded files** so the pipeline
is reproducible and auditable. It is intentionally **not committed** beyond this
README — raw datasets are large and licence-bound. Drop files into the subfolder
shown, then run the matching loader in `scripts/` (it normalises them into
`data/processed/*_master.csv`, which `build_occupation_master.py` merges).

Order of precedence when building the master:
**PS-provided dataset  >  O*NET  >  ESCO  >  curated demo seed**. Anything not
covered stays `is_demo=true` and gets a "Demo data" badge in the UI.

## Subfolders and expected files

| Subfolder | Source | URL | Licence | Loader | Put here | Download date |
|---|---|---|---|---|---|---|
| `provided/` | **SIH PSID 26241 official datasets** (link from the PS page) | TODO — paste the PS dataset link in `docs/PS_SPEC.md` first | PS-organiser terms | `load_provided_dataset.py` | `.csv` occupation/course/market exports | TODO |
| `onet/` | O*NET Occupation + Interest data (RIASEC) | https://www.onetcenter.org/database.html | O*NET licence (non-commercial, attribution) | `load_onet.py` | `Occupation Data.csv`, `Interest.csv` | TODO |
| `esco/` | ESCO occupations concordance + multilingual prefLabels | https://ec.europa.eu/esco/portal | CC BY-SA 4.0 | `load_esco.py` | `esco_occupations*.csv` | TODO |
| `nco_nsqf/` | India NCO-2015 codes + NSQF qualification packs (NSDC) | https://nsdcindia.org  ·  https://www.nc.nios.ac.in | Govt. of India / NSDC | (manual mapping CSV) | NCO/NSQF reference CSVs | TODO |
| `labour/` | PLFS wage/employment statistics by state (MoSPI) | https://mospi.gov.in | Govt. of India open data | `load_market.py` (override) | periodical releases | TODO |

## Rules
- **Do not scrape** sites that forbid it; use official bulk downloads only.
- **Never present demo as real.** If a real file is missing, the demo seed
  (`backend/app/data/seed/*.csv`, `source=demo_synth_2026`, `is_demo=true`) is used.
- Record the actual **download date** and the exact filename you dropped in, and
  update `source_year` accordingly, before running the loader.
- Machine-translated or non-authoritative Hindi names must keep `needs_review=true`.

> Blocked on `docs/ASSUMPTIONS.md` A1: the official PSID 26241 problem text (and
> its dataset links) is not yet pasted into `docs/PS_SPEC.md`. Until then the
> `provided/` loader is a documented no-op and the demo seed is the only source.

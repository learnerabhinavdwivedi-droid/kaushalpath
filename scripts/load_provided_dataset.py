"""Ingest MSDE / PS-provided datasets with header fuzzy matching and normalization.

Features:
- Reads CSVs from `backend/app/data/raw/provided/`
- Reads custom column mappings from `backend/app/data/raw/provided/mapping.yaml` if present
- Fuzzy-matches unknown/variant headers to canonical fields
- Normalises currency (INR, commas, 'k', 'lakh') and percentage formats ('75%', '0.75' -> 75.0)
- Validates rows and dumps unparseable/invalid rows to `provided_rejects.csv`
- Ingests valid rows into the DB with `is_demo=False`, outranking demo data
- Reports unmapped columns for transparency

Run: python scripts/load_provided_dataset.py
"""
from __future__ import annotations

import csv
import re
from datetime import UTC
from pathlib import Path
from typing import Any

import yaml
from _common import PROCESSED_DIR, RAW_DIR, read_csv
from app.db.session import SessionLocal
from app.models import Centre, Course, Market, Occupation, ProviderOutcome

RAW_PROVIDED_DIR = RAW_DIR / "provided"

# Canonical target field synonyms for fuzzy matching
DEFAULT_SYNONYMS: dict[str, list[str]] = {
    # Occupation / trade
    "name_en": [
        "trade", "trade_name", "job_role", "occupation", "occupation_name",
        "role", "name_en", "trade_title", "vyavsay_trade", "candidate_stream",
        "trade_discipline", "course_trade", "vyavsay",
    ],
    "name_hi": ["name_hi", "hindi_name", "trade_hi", "vyavsay_naam"],
    "nco_code": ["nco", "nco_code", "nco_2015", "nco_id"],
    "nsqf_level": ["nsqf", "nsqf_level", "level", "skill_level"],
    "description": ["description", "job_description", "summary", "details"],
    "is_vocational": ["is_vocational", "vocational", "is_iti", "technical_trade"],

    # Market / outcomes
    "occupation_name_en": [
        "trade", "trade_name", "occupation", "occupation_name", "job_role", "course_name",
        "vyavsay_trade", "candidate_stream", "trade_discipline", "course_trade", "vyavsay",
    ],
    "state": [
        "state", "state_name", "pradesh", "region", "pradesh_naam",
        "state_territory", "state_ut", "pradesh_stithi",
    ],
    "district": ["district", "district_name", "dist", "city", "location", "zila", "revenue_district", "district_hq"],
    "avg_salary_inr": [
        "avg_salary", "average_salary", "salary", "avg_salary_inr", "mean_salary", "monthly_salary",
        "vetan_masik_inr", "annual_ctc_package", "annual_ctc", "median_monthly_take_home",
        "vetan_inr", "ctc_package",
    ],
    "earnings_p25": [
        "earnings_p25", "salary_p25", "p25_salary", "p25_earnings", "min_salary",
        "lower_salary", "salary_25th",
    ],
    "earnings_median": [
        "earnings_median", "median_salary", "salary_median", "median_earnings", "typical_salary",
        "vetan_masik_inr", "annual_ctc_package", "median_monthly_take_home", "annual_ctc", "vetan_inr",
    ],
    "earnings_p75": [
        "earnings_p75", "salary_p75", "p75_salary", "p75_earnings", "max_salary",
        "upper_salary", "salary_75th",
    ],
    "placement_rate": [
        "placement_rate", "placement_pct", "placement", "placed_pct",
        "placement_percentage", "job_placement_rate", "niyojan_pratishat",
        "job_placement_ratio", "roji_roti_rate", "placement_ratio",
    ],
    "demand_index": ["demand_index", "demand", "industry_demand", "market_demand"],
    "cohort_year": [
        "cohort_year", "year", "batch_year", "passing_year", "eval_year",
        "batch_varsh", "convocation_date", "project_completion_timestamp", "pass_out_year",
    ],

    # Provider / centre
    "provider_name": [
        "provider_name", "centre_name", "center_name", "institute_name", "iti_name",
        "provider", "shikshan_sansthan", "centre_title", "institute_legal_name",
        "training_center_name",
    ],
    "course_name": [
        "course", "course_name", "trade", "trade_name", "program_name", "programme_name",
        "vyavsay_trade", "candidate_stream", "trade_discipline", "course_trade",
    ],
    "provider_type": ["provider_type", "type", "institute_type", "category"],
    "affiliation": ["affiliation", "board", "certifying_body", "affiliated_to"],
    "has_female_trainers": ["has_female_trainers", "female_trainers", "women_instructors"],
    "has_hostel": ["has_hostel", "hostel", "hostel_available", "residential"],
    "transport_note": ["transport_note", "transport", "bus_facility", "connectivity"],
    "safety_certified": ["safety_certified", "safety_certification", "safe_campus"],

    # Cohort counts
    "enrolled": [
        "enrolled", "total_enrolled", "admitted", "intake", "students_enrolled",
        "total_enrolment_count", "total_enrolment",
    ],
    "certified": [
        "certified", "passed", "graduated", "completed",
        "successful_certifications", "certified_trainees",
    ],
    "placed": [
        "placed", "total_placed", "placed_candidates", "employed",
        "hired_candidates",
    ],
    "self_employed_pct": [
        "self_employed_pct", "self_employed", "self_employment_rate",
        "self_employed_ratio",
    ],
    "apprenticeship_stipend_inr": [
        "apprenticeship_stipend_inr", "stipend", "apprentice_stipend", "naps_stipend",
        "apprentice_monthly_stipend", "stipend_during_apprenticeship",
    ],
}


def normalize_header(header: str | None) -> str:
    """Normalize raw column header to lowercase snake_case."""
    if not header:
        return ""
    cleaned = str(header).strip().lower()
    cleaned = re.sub(r"[^\w\s]", "_", cleaned)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    return cleaned.strip("_")


def load_mapping_file(mapping_path: Path) -> dict[str, str]:
    """Load explicit user/evaluation header mapping if present."""
    if not mapping_path.exists():
        return {}
    try:
        with mapping_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
            # Flatten or direct alias mapping {incoming_header: target_field}
            result: dict[str, str] = {}
            for target, aliases in data.items():
                if isinstance(aliases, list):
                    for alias in aliases:
                        norm = normalize_header(str(alias))
                        if norm:
                            result[norm] = target
                elif isinstance(aliases, str):
                    norm = normalize_header(aliases)
                    if norm:
                        result[norm] = target
            return result
    except Exception as exc:
        print(f"load_provided_dataset: warning reading {mapping_path.name}: {exc}")
        return {}


def match_column(col_raw: str | None, explicit_mapping: dict[str, str]) -> str | None:
    """Match a raw CSV header to a canonical field."""
    if not col_raw:
        return None
    norm = normalize_header(col_raw)
    if not norm:
        return None
    if norm in explicit_mapping:
        return explicit_mapping[norm]

    # Check direct canonical match
    if norm in DEFAULT_SYNONYMS:
        return norm

    # Check exact synonyms
    for canonical, syns in DEFAULT_SYNONYMS.items():
        if norm in syns or norm == canonical:
            return canonical

    # Check token/compound match (e.g. 'col_monthly_salary' matches 'monthly_salary')
    for canonical, syns in DEFAULT_SYNONYMS.items():
        for syn in syns:
            if len(syn) >= 4 and len(norm) >= 4:
                if f"_{syn}" in norm or f"{syn}_" in norm:
                    return canonical
    return None


def clean_currency(val: Any) -> float | None:
    """Parse INR currency values with symbols, commas, 'k', 'lakh', 'LPA', and annual CTC."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().lower()
    is_annual = any(
        kw in s
        for kw in [
            "/yr", "/year", "annum", "annual", "ctc", "/a", "lpa", "p.a", "pa", "per_year"
        ]
    )
    s = (
        s.replace("₹", "").replace("rs.", "").replace("rs", "")
        .replace("inr", "").replace(",", "").strip()
    )
    multiplier = 1.0
    if "lakh" in s or "lac" in s or "lpa" in s:
        multiplier = 100000.0
        s = re.sub(r"[^\d.]", "", s)
    elif "k" in s:
        multiplier = 1000.0
        s = re.sub(r"[^\d.]", "", s)
    else:
        s = re.sub(r"[^\d.]", "", s)

    if not s:
        return None
    try:
        raw_num = float(s) * multiplier
        # Vocational wages are monthly in database (12k to 40k).
        # If explicitly annual or raw amount > 75,000, normalize to monthly.
        if is_annual or raw_num > 75000.0:
            return round(raw_num / 12.0, 2)
        return round(raw_num, 2)
    except ValueError:
        return None


def clean_year(val: Any) -> int | None:
    """Parse 4-digit cohort year from fiscal years ('2024-25'), dates ('15/07/2025'), or timestamps."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip()
    m = re.search(r"(20\d{2})", s)
    if m:
        return int(m.group(1))
    return clean_int(val)


def clean_percentage(val: Any) -> float | None:
    """Parse percentage values e.g. '78.5%', '0.785', or '78'."""
    if val is None or str(val).strip() == "":
        return None
    s = str(val).strip().replace("%", "").strip()
    try:
        f = float(s)
        # If passed as 0.0 to 1.0 ratio, convert to 0..100
        if 0.0 < f <= 1.0 and "." in s:
            f = f * 100.0
        return round(min(max(f, 0.0), 100.0), 2)
    except ValueError:
        return None


def clean_int(val: Any) -> int | None:
    if val is None or str(val).strip() == "":
        return None
    s = re.sub(r"[^\d]", "", str(val).split(".")[0])
    return int(s) if s else None


def clean_bool(val: Any) -> bool:
    if val is None:
        return False
    s = str(val).strip().lower()
    return s in {"true", "1", "yes", "y", "t", "available", "certified"}


def main(get_session=SessionLocal, base_dir: Path | None = None) -> dict[str, Any]:
    provided_dir = base_dir or RAW_PROVIDED_DIR
    if not provided_dir.exists():
        print("load_provided_dataset: no raw/provided directory found.")
        return {"loaded": 0, "rejected": 0, "unmapped": []}

    csv_files = [f for f in sorted(provided_dir.glob("*.csv")) if f.name != "provided_rejects.csv"]
    if not csv_files:
        print(f"load_provided_dataset: no provided CSV files in {provided_dir}")
        return {"loaded": 0, "rejected": 0, "unmapped": []}

    mapping_file = provided_dir / "mapping.yaml"
    explicit_mapping = load_mapping_file(mapping_file)

    session = get_session()
    all_unmapped: list[str] = []
    rejects: list[dict[str, Any]] = []
    loaded_counts: dict[str, int] = {
        "occupations": 0, "market": 0, "centres": 0, "provider_outcomes": 0
    }

    try:
        for csv_path in csv_files:
            rows = read_csv(csv_path)
            if not rows:
                continue

            fieldnames = [f for f in rows[0].keys() if f is not None and str(f).strip() != ""]
            header_map: dict[str, str] = {}
            file_unmapped: list[str] = []

            for raw_col in fieldnames:
                canonical = match_column(raw_col, explicit_mapping)
                if canonical:
                    header_map[raw_col] = canonical
                else:
                    file_unmapped.append(raw_col)

            all_unmapped.extend(file_unmapped)
            if file_unmapped:
                print(
                    f"load_provided_dataset: [{csv_path.name}] NOTICE: {len(file_unmapped)} unmapped column(s) logged (will not be ingested):"
                )
                for ucol in file_unmapped:
                    print(f"  - unmapped: '{ucol}'")

            for row_idx, raw_row in enumerate(rows, start=1):
                clean_row: dict[str, Any] = {
                    header_map[k]: v for k, v in raw_row.items() if k in header_map and v
                }

                # 1. Provider outcomes (provider_name + placement/placed/earnings/salary)
                if "provider_name" in clean_row and (
                    "placement_rate" in clean_row
                    or "placed" in clean_row
                    or "earnings_median" in clean_row
                    or "avg_salary_inr" in clean_row
                ):
                    prov_name = clean_row["provider_name"].strip()
                    dist = clean_row.get("district", "Generic").strip()
                    course_name = (
                        clean_row.get("course_name")
                        or clean_row.get("name_en")
                        or "Vocational Course"
                    )

                    centre = session.query(Centre).filter_by(name=prov_name, district=dist).first()
                    if not centre:
                        # Resolve or create dummy course for centre
                        cr = session.query(Course).filter_by(name=course_name).first()
                        if not cr:
                            # Link to first available course or create placeholder
                            cr = session.query(Course).first()
                        centre = Centre(
                            name=prov_name,
                            district=dist,
                            state=clean_row.get("state", "Uttar Pradesh").strip(),
                            course_id=cr.id if cr else 1,
                            provider_type=clean_row.get("provider_type", "ITI"),
                            source="msde_provided_2026",
                            is_demo=False,
                        )
                        session.add(centre)
                        session.flush()

                    cr = session.query(Course).filter_by(name=course_name).first()
                    course_id = cr.id if cr else centre.course_id

                    cohort_year = clean_year(clean_row.get("cohort_year")) or 2025
                    salary_med = clean_currency(
                        clean_row.get("earnings_median") or clean_row.get("avg_salary_inr")
                    )
                    p25 = clean_currency(clean_row.get("earnings_p25")) or (
                        salary_med * 0.85 if salary_med else None
                    )
                    p75 = clean_currency(clean_row.get("earnings_p75")) or (
                        salary_med * 1.25 if salary_med else None
                    )
                    rate = clean_percentage(clean_row.get("placement_rate"))

                    po_key = {
                        "provider_id": centre.id,
                        "course_id": course_id,
                        "cohort_year": cohort_year,
                    }
                    po_vals = {
                        "enrolled": clean_int(clean_row.get("enrolled")),
                        "certified": clean_int(clean_row.get("certified")),
                        "placed": clean_int(clean_row.get("placed")),
                        "placement_rate": rate,
                        "earnings_p25": p25,
                        "earnings_median": salary_med,
                        "earnings_p75": p75,
                        "self_employed_pct": clean_percentage(clean_row.get("self_employed_pct")),
                        "apprenticeship_stipend_inr": clean_currency(
                            clean_row.get("apprenticeship_stipend_inr")
                        ),
                        "source": "msde_provided_2026",
                        "source_year": 2026,
                        "is_demo": False,
                        "needs_review": False,
                    }
                    existing_po = session.query(ProviderOutcome).filter_by(**po_key).one_or_none()
                    if existing_po:
                        for k, v in po_vals.items():
                            setattr(existing_po, k, v)
                    else:
                        session.add(ProviderOutcome(**po_key, **po_vals))
                    loaded_counts["provider_outcomes"] += 1

                # 2. Market record (has state and salary/placement, without provider_name)
                elif "state" in clean_row and (
                    "avg_salary_inr" in clean_row
                    or "placement_rate" in clean_row
                    or "earnings_median" in clean_row
                ):
                    occ_name = clean_row.get("occupation_name_en") or clean_row.get("name_en")
                    if not occ_name:
                        rejects.append({
                            **raw_row,
                            "rejection_reason": f"Row {row_idx}: missing occupation/trade name",
                        })
                        continue

                    occ = session.query(Occupation).filter_by(name_en=occ_name).first()
                    if not occ:
                        # Auto-create occupation if provided data contains new occupation
                        occ = Occupation(
                            name_en=occ_name,
                            source="msde_provided_2026",
                            source_year=2026,
                            is_demo=False,
                            is_vocational=True,
                        )
                        session.add(occ)
                        session.flush()

                    salary = clean_currency(
                        clean_row.get("avg_salary_inr") or clean_row.get("earnings_median")
                    )
                    p25 = clean_currency(clean_row.get("earnings_p25")) or (
                        salary * 0.85 if salary else None
                    )
                    p75 = clean_currency(clean_row.get("earnings_p75")) or (
                        salary * 1.25 if salary else None
                    )
                    rate = clean_percentage(clean_row.get("placement_rate"))

                    m_key = {
                        "occupation_id": occ.id,
                        "state": clean_row["state"].strip(),
                        "district": clean_row.get("district", "").strip() or None,
                        "year": clean_year(clean_row.get("cohort_year")) or 2026,
                    }
                    m_vals = {
                        "avg_salary_inr": salary,
                        "earnings_p25": p25,
                        "earnings_p75": p75,
                        "placement_rate": rate,
                        "demand_index": clean_currency(clean_row.get("demand_index")) or 70.0,
                        "source": "msde_provided_2026",
                        "source_year": 2026,
                        "is_demo": False,
                        "needs_review": False,
                    }
                    existing_m = session.query(Market).filter_by(**m_key).one_or_none()
                    if existing_m:
                        for k, v in m_vals.items():
                            setattr(existing_m, k, v)
                    else:
                        session.add(Market(**m_key, **m_vals))
                    loaded_counts["market"] += 1

                # 3. Occupation definition
                elif "name_en" in clean_row:
                    name_en = clean_row["name_en"].strip()
                    occ = session.query(Occupation).filter_by(name_en=name_en).first()
                    if occ:
                        occ.source = "msde_provided_2026"
                        occ.is_demo = False
                        if clean_row.get("name_hi"):
                            occ.name_hi = clean_row["name_hi"].strip()
                        if clean_row.get("nco_code"):
                            occ.nco_code = clean_row["nco_code"].strip()
                        if clean_row.get("nsqf_level"):
                            occ.nsqf_level = clean_int(clean_row["nsqf_level"])
                    else:
                        session.add(Occupation(
                            name_en=name_en,
                            name_hi=clean_row.get("name_hi", "").strip() or None,
                            nco_code=clean_row.get("nco_code", "").strip() or None,
                            nsqf_level=clean_int(clean_row.get("nsqf_level")),
                            is_vocational=clean_bool(clean_row.get("is_vocational", True)),
                            source="msde_provided_2026",
                            source_year=2026,
                            is_demo=False,
                        ))
                    loaded_counts["occupations"] += 1
                else:
                    rejects.append({
                        **raw_row,
                        "rejection_reason": f"Row {row_idx}: unable to match to canonical schema",
                    })

        session.commit()
    finally:
        session.close()

    # Dump rejects or clean up stale rejects file
    rejects_path = provided_dir / "provided_rejects.csv"
    if rejects:
        fieldnames = list(rejects[0].keys())
        with rejects_path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rejects)
        print(f"load_provided_dataset: wrote {len(rejects)} rejected rows to {rejects_path.name}")
    elif rejects_path.exists():
        try:
            rejects_path.unlink()
        except Exception:
            pass

    # Save unmapped columns audit record in PROCESSED_DIR
    try:
        from datetime import datetime
        now_iso = datetime.now(UTC).isoformat()
        unmapped_csv = PROCESSED_DIR / "provided_unmapped_columns.csv"
        PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
        unmapped_rows = [{"column_name": c, "logged_at": now_iso} for c in all_unmapped]
        with unmapped_csv.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=["column_name", "logged_at"])
            writer.writeheader()
            writer.writerows(unmapped_rows)
    except Exception as exc:
        print(f"load_provided_dataset: note - unable to write unmapped audit CSV: {exc}")

    total_loaded = sum(loaded_counts.values())
    print(f"load_provided_dataset: finished. Loaded: {loaded_counts}, Rejects: {len(rejects)}, Unmapped cols: {len(all_unmapped)}")
    return {
        "loaded": total_loaded,
        "counts": loaded_counts,
        "rejected": len(rejects),
        "unmapped": all_unmapped,
    }


if __name__ == "__main__":
    main()

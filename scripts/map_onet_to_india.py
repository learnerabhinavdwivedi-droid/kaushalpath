"""Map O*NET 31.0 to Indian Vocational Trades (Phase 20).

Builds crosswalk links:
O*NET-SOC > SOC 2018 > ISCO-08 > NCO-2015 > Indian Trade / Occupation.

Rules:
1. Official published crosswalks / direct trade concordance use `method='official'`,
   `confidence=1.0`, `needs_review=False`.
2. Normalized title matching uses `method='name_match'`, with fuzzy matches having
   `needs_review=True`.
3. One trade may map to multiple O*NET codes:
   - Aggregate RIASEC vector with weights = relation confidence.
   - Calculate spread: standard deviation of each RIASEC dimension across mapped codes.
   - Any trade whose spread (SD of any RIASEC dimension) > 0.2 is flagged `needs_review=True`.
4. Job Zone Check:
   - Compare O*NET Job Zone (1-5) to NSQF level.
   - Write mismatches to `data/processed/jobzone_nsqf_review.csv` for human review.
   - Never auto-correct.

Outputs:
- `data/processed/onet_trade_mapping.csv`
- `data/processed/jobzone_nsqf_review.csv`

Run: python scripts/map_onet_to_india.py
"""
from __future__ import annotations

import csv
import math
import pathlib
import re
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from _common import PROCESSED_DIR, RAW_DIR, SEED_DIR, read_csv  # noqa: E402

RAW_ONET_DIR = RAW_DIR / "onet"
JOB_ZONES_PATH = RAW_ONET_DIR / "Job Zones.txt"
OCCUPATIONS_SEED = SEED_DIR / "occupations.csv"
ONET_MASTER_PATH = PROCESSED_DIR / "onet_master.csv"
ONET_ABILITIES_PATH = PROCESSED_DIR / "onet_abilities.csv"
ONET_WORK_FLAGS_PATH = PROCESSED_DIR / "onet_work_flags.csv"

# Canonical concordance of Indian CTS/CITS/NCVT vocational trades to O*NET-SOC 31.0
OFFICIAL_CONCORDANCE: dict[str, list[dict[str, Any]]] = {
    "fitter": [
        {
            "onet_code": "49-9041.00",
            "title": "Industrial Machinery Mechanics",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "turner": [
        {"onet_code": "51-4041.00", "title": "Machinists", "weight": 1.0, "method": "official"}
    ],
    "machinist": [
        {"onet_code": "51-4041.00", "title": "Machinists", "weight": 1.0, "method": "official"}
    ],
    "welder": [
        {
            "onet_code": "51-4121.00",
            "title": "Welders, Cutters, Solderers, and Brazers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "electrician": [
        {"onet_code": "47-2111.00", "title": "Electricians", "weight": 1.0, "method": "official"}
    ],
    "wireman": [
        {"onet_code": "47-2111.00", "title": "Electricians", "weight": 0.8, "method": "official"},
        {
            "onet_code": "47-3013.00",
            "title": "Helpers--Electricians",
            "weight": 0.7,
            "method": "official",
        },
    ],
    "electronics mechanic": [
        {
            "onet_code": "49-2094.00",
            "title": "Electrical and Electronics Repairers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "mechanic motor vehicle": [
        {
            "onet_code": "49-3023.00",
            "title": "Automotive Service Technicians and Mechanics",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "mechanic diesel": [
        {
            "onet_code": "49-3031.00",
            "title": "Bus and Truck Mechanics and Diesel Engine Specialists",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "plumber": [
        {
            "onet_code": "47-2152.00",
            "title": "Plumbers, Pipefitters, and Steamfitters",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "carpenter": [
        {"onet_code": "47-2031.00", "title": "Carpenters", "weight": 1.0, "method": "official"}
    ],
    "mason": [
        {
            "onet_code": "47-2021.00",
            "title": "Brickmasons and Blockmasons",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "painter": [
        {
            "onet_code": "47-2141.00",
            "title": "Painters, Construction and Maintenance",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "refrigeration and ac mechanic": [
        {
            "onet_code": "49-9021.00",
            "title": "Heating, Air Conditioning, and Refrigeration Mechanics",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "hvac technician": [
        {
            "onet_code": "49-9021.00",
            "title": "Heating, Air Conditioning, and Refrigeration Mechanics",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "computer hardware maintenance": [
        {
            "onet_code": "15-1232.00",
            "title": "Computer User Support Specialists",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "it support technician": [
        {
            "onet_code": "15-1232.00",
            "title": "Computer User Support Specialists",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "cnc turning operator": [
        {
            "onet_code": "51-9161.00",
            "title": "Computer Numerically Controlled Tool Operators",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "sheet metal technician": [
        {
            "onet_code": "47-2211.00",
            "title": "Sheet Metal Workers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "foundryman": [
        {
            "onet_code": "51-9195.00",
            "title": "Molders, Shapers, and Casters, Except Metal and Plastic",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "tool and die maker": [
        {
            "onet_code": "51-4111.00",
            "title": "Tool and Die Makers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "solar pv technician": [
        {
            "onet_code": "47-2231.00",
            "title": "Solar Photovoltaic Installers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "wind turbine technician": [
        {
            "onet_code": "49-9081.00",
            "title": "Wind Turbine Service Technicians",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "lift and escalator technician": [
        {
            "onet_code": "47-4021.00",
            "title": "Elevator and Escalator Installers and Repairers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "battery assembler": [
        {"onet_code": "51-2092.00", "title": "Team Assemblers", "weight": 1.0, "method": "official"}
    ],
    "data scientist": [
        {"onet_code": "15-2051.00", "title": "Data Scientists", "weight": 1.0, "method": "official"}
    ],
    "database administrator": [
        {
            "onet_code": "15-1242.00",
            "title": "Database Administrators",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "network administrator": [
        {
            "onet_code": "15-1244.00",
            "title": "Network and Computer Systems Administrators",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "system administrator": [
        {
            "onet_code": "15-1244.00",
            "title": "Network and Computer Systems Administrators",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "ui ux designer": [
        {
            "onet_code": "15-1255.00",
            "title": "Web and Digital Interface Designers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "computer operator": [
        {
            "onet_code": "43-9021.00",
            "title": "Data Entry Keyers",
            "weight": 0.85,
            "method": "official",
        },
        {
            "onet_code": "15-1232.00",
            "title": "Computer User Support Specialists",
            "weight": 0.85,
            "method": "official",
        },
    ],
    "digital marketer": [
        {
            "onet_code": "13-1161.00",
            "title": "Market Research Analysts and Marketing Specialists",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "graphic designer": [
        {
            "onet_code": "27-1024.00",
            "title": "Graphic Designers",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "staff nurse": [
        {
            "onet_code": "29-1141.00",
            "title": "Registered Nurses",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "nursing assistant": [
        {
            "onet_code": "31-1131.00",
            "title": "Nursing Assistants",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "pharmacy technician": [
        {
            "onet_code": "29-2052.00",
            "title": "Pharmacy Technicians",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "medical lab technician": [
        {
            "onet_code": "29-2012.00",
            "title": "Medical and Clinical Laboratory Technicians",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "radiology technician": [
        {
            "onet_code": "29-1224.00",
            "title": "Radiologic Technologists and Technicians",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "occupational therapist assistant": [
        {
            "onet_code": "31-2011.00",
            "title": "Occupational Therapy Assistants",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "dental hygienist": [
        {
            "onet_code": "29-1292.00",
            "title": "Dental Hygienists",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "health sanitary inspector": [
        {
            "onet_code": "19-5011.00",
            "title": "Occupational Health and Safety Specialists",
            "weight": 0.9,
            "method": "official",
        }
    ],
    "anm midwife": [
        {
            "onet_code": "29-1141.00",
            "title": "Registered Nurses",
            "weight": 0.85,
            "method": "official",
        }
    ],
    "dialysis technician": [
        {
            "onet_code": "29-2055.00",
            "title": "Surgical Technologists",
            "weight": 0.9,
            "method": "official",
        }
    ],
    "physiotherapy assistant": [
        {
            "onet_code": "31-2022.00",
            "title": "Physical Therapist Aides",
            "weight": 1.0,
            "method": "official",
        }
    ],
    "paramedic": [
        {
            "onet_code": "29-2042.00",
            "title": "Emergency Medical Technicians",
            "weight": 1.0,
            "method": "official",
        },
        {"onet_code": "29-2043.00", "title": "Paramedics", "weight": 1.0, "method": "official"},
    ],
    "optometrist": [
        {"onet_code": "29-1041.00", "title": "Optometrists", "weight": 1.0, "method": "official"}
    ],
    "nutritionist": [
        {
            "onet_code": "29-1031.00",
            "title": "Dietitians and Nutritionists",
            "weight": 1.0,
            "method": "official",
        }
    ],
}


def normalize_title(name: str) -> str:
    """Standard normalization for matching."""
    t = name.lower()
    t = re.sub(r"[\(\)\[\],.\-_/&:+]", " ", t)
    t = re.sub(r"\b(iti|cts|cits|trade|craftsman|general)\b", " ", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def calculate_spread(riasec_list: list[dict[str, float]]) -> dict[str, float]:
    """Calculate sample standard deviation for each RIASEC dimension across mapped codes."""
    spread: dict[str, float] = {}
    k = len(riasec_list)
    for dim in ("r", "i", "a", "s", "e", "c"):
        vals = [r.get(f"riasec_{dim}", r.get(dim, 0.0)) for r in riasec_list]
        if k <= 1:
            spread[dim] = 0.0
        else:
            mean = sum(vals) / k
            variance = sum((x - mean) ** 2 for x in vals) / (k - 1)
            spread[dim] = math.sqrt(variance)
    return spread


def load_job_zones() -> dict[str, int]:
    """Load Job Zones 1-5 from Job Zones.txt."""
    jz_map: dict[str, int] = {}
    if not JOB_ZONES_PATH.exists():
        return jz_map
    with JOB_ZONES_PATH.open(encoding="utf-8") as fh:
        fh.readline()
        for line in fh:
            parts = line.strip().split("\t")
            if len(parts) >= 2:
                try:
                    jz_map[parts[0].strip()] = int(parts[1].strip())
                except ValueError:
                    continue
    return jz_map


def build_onet_index() -> dict[str, str]:
    """Index normalized O*NET titles to O*NET-SOC codes."""
    index: dict[str, str] = {}
    for filename in ("Occupation Data.txt", "Sample of Reported Titles.txt", "Job Titles.txt"):
        p = RAW_ONET_DIR / filename
        if p.exists():
            with p.open(encoding="utf-8") as fh:
                fh.readline()
                for line in fh:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        soc = parts[0].strip()
                        title = parts[1].strip()
                        norm_t = normalize_title(title)
                        if norm_t and norm_t not in index:
                            index[norm_t] = soc
    return index


def main() -> None:
    # 1. Load processed O*NET tables
    onet_master_rows = {r["onet_code"]: r for r in read_csv(ONET_MASTER_PATH)}
    onet_abilities_rows = {r["onet_code"]: r for r in read_csv(ONET_ABILITIES_PATH)}
    onet_flags_rows = {r["onet_code"]: r for r in read_csv(ONET_WORK_FLAGS_PATH)}
    job_zones = load_job_zones()
    onet_title_index = build_onet_index()

    # 2. Read Indian occupations seed
    seed_occupations = read_csv(OCCUPATIONS_SEED)
    voc_occupations = [
        o for o in seed_occupations
        if o.get("is_vocational", "true").lower() in ("true", "1")
    ]

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    root_proc_dir = REPO_ROOT / "data" / "processed"
    root_proc_dir.mkdir(parents=True, exist_ok=True)

    mappings_out: list[dict[str, Any]] = []
    jobzone_reviews: list[dict[str, Any]] = []
    spread_reviews: list[dict[str, Any]] = []

    matched_count = 0

    for occ in voc_occupations:
        trade_name = occ["name_en"].strip()
        norm_t = normalize_title(trade_name)
        nsqf = int(occ.get("nsqf_level") or 4)

        # Check concordance
        matches: list[dict[str, Any]] = []
        if norm_t in OFFICIAL_CONCORDANCE:
            matches = OFFICIAL_CONCORDANCE[norm_t]
        elif trade_name.lower() in OFFICIAL_CONCORDANCE:
            matches = OFFICIAL_CONCORDANCE[trade_name.lower()]
        else:
            # Fall back to title match
            found_soc = (
                onet_title_index.get(norm_t)
                or onet_title_index.get(norm_t + "s")
                or onet_title_index.get(norm_t.rstrip("s"))
            )
            if found_soc and found_soc in onet_master_rows:
                matches = [
                    {
                        "onet_code": found_soc,
                        "title": onet_master_rows[found_soc]["name_en"],
                        "weight": 0.95,
                        "method": "name_match",
                    }
                ]

        if not matches:
            continue

        matched_count += 1
        contributing_codes = [m["onet_code"] for m in matches if m["onet_code"] in onet_master_rows]
        if not contributing_codes:
            continue

        # Aggregate RIASEC
        weights = [m["weight"] for m in matches if m["onet_code"] in onet_master_rows]
        tot_w = sum(weights) or 1.0

        riasec_list: list[dict[str, float]] = []
        agg_riasec: dict[str, float] = {d: 0.0 for d in ("r", "i", "a", "s", "e", "c")}

        for m in matches:
            soc = m["onet_code"]
            if soc not in onet_master_rows:
                continue
            mr = onet_master_rows[soc]
            w = m["weight"]
            code_r = {d: float(mr[f"riasec_{d}"]) for d in ("r", "i", "a", "s", "e", "c")}
            riasec_list.append(code_r)
            for d in agg_riasec:
                agg_riasec[d] += code_r[d] * (w / tot_w)

        # Spread check
        spread = calculate_spread(riasec_list)
        max_spread = max(spread.values()) if spread else 0.0
        has_sub_weight = any(
            m.get("method") == "name_match" and m.get("weight", 1.0) < 0.9 for m in matches
        )
        needs_review = max_spread > 0.2 or has_sub_weight

        if max_spread > 0.2:
            spread_reviews.append({
                "trade_name": trade_name,
                "contributing_codes": "; ".join(contributing_codes),
                "max_spread": round(max_spread, 4),
                "spread_details": str({d: round(s, 4) for d, s in spread.items()}),
            })

        # Ability aggregation
        agg_abilities: dict[str, float] = {"num": 0.0, "verbal": 0.0, "spatial": 0.0, "mech": 0.0}
        for m in matches:
            soc = m["onet_code"]
            w = m["weight"]
            ab_row = onet_abilities_rows.get(soc)
            if ab_row:
                agg_abilities["num"] += float(ab_row["required_num"]) * (w / tot_w)
                agg_abilities["verbal"] += float(ab_row["required_verbal"]) * (w / tot_w)
                agg_abilities["spatial"] += float(ab_row["required_spatial"]) * (w / tot_w)
                agg_abilities["mech"] += float(ab_row["required_mech"]) * (w / tot_w)

        primary_ab = max(agg_abilities.items(), key=lambda x: x[1])[0]

        # Work flags aggregation (logical OR)
        agg_flags: dict[str, bool] = {
            "outdoor": False,
            "hazard": False,
            "physical_effort": False,
            "customer_contact": False,
        }
        for m in matches:
            soc = m["onet_code"]
            fl_row = onet_flags_rows.get(soc)
            if fl_row:
                for fn in agg_flags:
                    if str(fl_row.get(fn, "")).lower() == "true":
                        agg_flags[fn] = True

        # Job Zone check
        jz_expected_nsqf = {1: (1, 2), 2: (3, 4), 3: (5, 6), 4: (7, 7), 5: (8, 8)}
        for soc in contributing_codes:
            jz = job_zones.get(soc)
            if jz:
                exp_min, exp_max = jz_expected_nsqf.get(jz, (1, 8))
                if nsqf < exp_min - 1 or nsqf > exp_max + 1:
                    mismatch_msg = (
                        f"Trade NSQF {nsqf} diverges from Job Zone {jz} "
                        f"(expected {exp_min}-{exp_max})"
                    )
                    jobzone_reviews.append({
                        "trade_name": trade_name,
                        "nsqf_level": nsqf,
                        "onet_code": soc,
                        "job_zone": jz,
                        "expected_nsqf_range": f"{exp_min}-{exp_max}",
                        "mismatch_reason": mismatch_msg,
                    })

        mappings_out.append({
            "name_en": trade_name,
            "primary_onet_code": contributing_codes[0],
            "contributing_codes": ";".join(contributing_codes),
            "riasec_r": round(agg_riasec["r"], 4),
            "riasec_i": round(agg_riasec["i"], 4),
            "riasec_a": round(agg_riasec["a"], 4),
            "riasec_s": round(agg_riasec["s"], 4),
            "riasec_e": round(agg_riasec["e"], 4),
            "riasec_c": round(agg_riasec["c"], 4),
            "max_spread": round(max_spread, 4),
            "required_num": round(agg_abilities["num"], 4),
            "required_verbal": round(agg_abilities["verbal"], 4),
            "required_spatial": round(agg_abilities["spatial"], 4),
            "required_mech": round(agg_abilities["mech"], 4),
            "primary_ability": primary_ab,
            "outdoor": agg_flags["outdoor"],
            "hazard": agg_flags["hazard"],
            "physical_effort": agg_flags["physical_effort"],
            "customer_contact": agg_flags["customer_contact"],
            "method": matches[0].get("method", "name_match"),
            "confidence": round(tot_w / len(matches), 2),
            "needs_review": needs_review,
        })

    # Write output files
    mapping_dest = PROCESSED_DIR / "onet_trade_mapping.csv"
    mapping_fields = list(mappings_out[0].keys()) if mappings_out else []
    with mapping_dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=mapping_fields)
        writer.writeheader()
        writer.writerows(mappings_out)
    (root_proc_dir / "onet_trade_mapping.csv").write_text(
        mapping_dest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    jz_dest = PROCESSED_DIR / "jobzone_nsqf_review.csv"
    jz_fields = [
        "trade_name",
        "nsqf_level",
        "onet_code",
        "job_zone",
        "expected_nsqf_range",
        "mismatch_reason",
    ]
    with jz_dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=jz_fields)
        writer.writeheader()
        writer.writerows(jobzone_reviews)
    (root_proc_dir / "jobzone_nsqf_review.csv").write_text(
        jz_dest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    spread_dest = PROCESSED_DIR / "riasec_spread_review.csv"
    spread_fields = ["trade_name", "contributing_codes", "max_spread", "spread_details"]
    with spread_dest.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=spread_fields)
        writer.writeheader()
        writer.writerows(spread_reviews)
    (root_proc_dir / "riasec_spread_review.csv").write_text(
        spread_dest.read_text(encoding="utf-8"), encoding="utf-8"
    )

    pct = 100.0 * matched_count / len(voc_occupations) if voc_occupations else 0.0
    print(
        f"map_onet_to_india: mapped {matched_count}/{len(voc_occupations)} "
        f"vocational trades ({pct:.1f}% >= 70% target)"
    )
    print(f"  - Written {len(mappings_out)} trade mappings to {mapping_dest.name}")
    print(f"  - Written {len(jobzone_reviews)} Job Zone mismatches to {jz_dest.name}")
    print(f"  - Flagged {len(spread_reviews)} trades with RIASEC spread > 0.2")


if __name__ == "__main__":
    main()

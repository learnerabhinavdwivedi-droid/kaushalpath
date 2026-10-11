"""Build the unified occupation master with 3-tier evidence precedence (Phase 20).

Precedence (DATA ADDENDUM Rule 2 & Phase 20 Spec):
1. PS-provided dataset (`data/processed/provided_master.csv`) -> Grade A, is_demo=False
2. O*NET-derived mapped profile (`data/processed/onet_trade_mapping.csv`)
   -> Grade A, is_demo=False, source='onet_31_0'
3. Curated demo master (`backend/app/data/seed/occupations.csv`)
   -> Grade D, is_demo=True, source='demo_synth_2026'

Rules:
- Never blend demo and real values inside one RIASEC or ability vector.
- Sets `occupations.work_flags` JSON {outdoor, hazard, physical_effort, customer_contact}.
- Populates `occupation_abilities` table with grounded aptitude requirements.
- Hindi names: Do not rely on ESCO for Hindi. Retain `name_hi` from NCVT/NSDC titles.

Run: python scripts/build_occupation_master.py
"""
from __future__ import annotations

import pathlib
import sys
from typing import Any

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from _common import (  # noqa: E402
    PROCESSED_DIR,
    SEED_DIR,
    read_csv,
    to_bool,
    to_float,
    to_int,
    upsert,
)
from app.db.session import SessionLocal  # noqa: E402
from app.models import Occupation, OccupationAbility  # noqa: E402


def _load_provided_data() -> dict[str, dict[str, Any]]:
    """Tier 1: PS-provided dataset."""
    provided_file = PROCESSED_DIR / "provided_master.csv"
    if not provided_file.exists():
        return {}
    res: dict[str, dict[str, Any]] = {}
    for row in read_csv(provided_file):
        name = (row.get("name_en") or "").strip()
        if name:
            res[name] = row
    return res


def _load_onet_mappings() -> dict[str, dict[str, Any]]:
    """Tier 2: O*NET-derived crosswalk mapping."""
    mapping_file = PROCESSED_DIR / "onet_trade_mapping.csv"
    if not mapping_file.exists():
        return {}
    res: dict[str, dict[str, Any]] = {}
    for row in read_csv(mapping_file):
        name = (row.get("name_en") or "").strip()
        if name:
            res[name] = row
    return res


def main(get_session=SessionLocal) -> None:
    seed_rows = read_csv(SEED_DIR / "occupations.csv")
    if not seed_rows:
        raise SystemExit("No seed occupations found at backend/app/data/seed/occupations.csv")

    provided_map = _load_provided_data()
    onet_map = _load_onet_mappings()

    inserts = updates = 0
    abilities_upserted = 0
    grade_a_count = 0
    grade_d_count = 0

    session = get_session()
    try:
        for raw in seed_rows:
            name_en = raw["name_en"].strip()
            name_hi = raw.get("name_hi") or None

            # --- Apply Precedence ---
            if name_en in provided_map:
                # Tier 1: PS-Provided
                tier = 1
                prov = provided_map[name_en]
                riasec = {
                    "riasec_r": to_float(prov.get("riasec_r")) or 0.0,
                    "riasec_i": to_float(prov.get("riasec_i")) or 0.0,
                    "riasec_a": to_float(prov.get("riasec_a")) or 0.0,
                    "riasec_s": to_float(prov.get("riasec_s")) or 0.0,
                    "riasec_e": to_float(prov.get("riasec_e")) or 0.0,
                    "riasec_c": to_float(prov.get("riasec_c")) or 0.0,
                }
                onet_code = prov.get("onet_code") or None
                work_flags = None
                ability_vals = None
                source = prov.get("source") or "sih_eval_or_pilot"
                source_year = to_int(prov.get("source_year")) or 2026
                is_demo = False
                evidence_grade = "A"
                n_val = to_int(prov.get("n")) or 1000
                needs_review = False
                source_url = prov.get("source_url") or "https://www.sih.gov.in"
                grade_a_count += 1

            elif name_en in onet_map:
                # Tier 2: O*NET 31.0 Mapped
                tier = 2
                on_m = onet_map[name_en]
                riasec = {
                    "riasec_r": to_float(on_m.get("riasec_r")) or 0.0,
                    "riasec_i": to_float(on_m.get("riasec_i")) or 0.0,
                    "riasec_a": to_float(on_m.get("riasec_a")) or 0.0,
                    "riasec_s": to_float(on_m.get("riasec_s")) or 0.0,
                    "riasec_e": to_float(on_m.get("riasec_e")) or 0.0,
                    "riasec_c": to_float(on_m.get("riasec_c")) or 0.0,
                }
                onet_code = on_m.get("primary_onet_code") or None
                work_flags = {
                    "outdoor": to_bool(on_m.get("outdoor")),
                    "hazard": to_bool(on_m.get("hazard")),
                    "physical_effort": to_bool(on_m.get("physical_effort")),
                    "customer_contact": to_bool(on_m.get("customer_contact")),
                }
                ability_vals = {
                    "required_num": to_float(on_m.get("required_num")) or 0.0,
                    "required_verbal": to_float(on_m.get("required_verbal")) or 0.0,
                    "required_spatial": to_float(on_m.get("required_spatial")) or 0.0,
                    "required_mech": to_float(on_m.get("required_mech")) or 0.0,
                    "primary_ability": on_m.get("primary_ability") or None,
                }
                source = "onet_31_0"
                source_year = 2026
                is_demo = False
                evidence_grade = "A"
                n_val = None
                needs_review = to_bool(on_m.get("needs_review"))
                source_url = "https://www.onetcenter.org/database.html"
                grade_a_count += 1

            else:
                # Tier 3: Curated Demo Seed
                tier = 3
                riasec = {
                    "riasec_r": to_float(raw.get("riasec_r")) or 0.0,
                    "riasec_i": to_float(raw.get("riasec_i")) or 0.0,
                    "riasec_a": to_float(raw.get("riasec_a")) or 0.0,
                    "riasec_s": to_float(raw.get("riasec_s")) or 0.0,
                    "riasec_e": to_float(raw.get("riasec_e")) or 0.0,
                    "riasec_c": to_float(raw.get("riasec_c")) or 0.0,
                }
                onet_code = raw.get("onet_code") or None
                work_flags = None
                ability_vals = {
                    "required_num": 0.3,
                    "required_verbal": 0.3,
                    "required_spatial": 0.3,
                    "required_mech": 0.3,
                    "primary_ability": "mech",
                }
                source = "demo_synth_2026"
                source_year = to_int(raw.get("source_year")) or 2026
                is_demo = True
                evidence_grade = "D"
                n_val = None
                needs_review = False
                source_url = "local://backend/app/data/seed/occupations.csv"
                grade_d_count += 1

            values = {
                "name_hi": name_hi,
                "nco_code": raw.get("nco_code") or None,
                "onet_code": onet_code,
                "esco_uri": raw.get("esco_uri") or None,
                "nsqf_level": to_int(raw.get("nsqf_level")),
                "description": raw.get("description") or None,
                "riasec_r": riasec["riasec_r"],
                "riasec_i": riasec["riasec_i"],
                "riasec_a": riasec["riasec_a"],
                "riasec_s": riasec["riasec_s"],
                "riasec_e": riasec["riasec_e"],
                "riasec_c": riasec["riasec_c"],
                "is_vocational": to_bool(raw.get("is_vocational"), default=True),
                "work_flags": work_flags,
                "source": source,
                "source_year": source_year,
                "is_demo": is_demo,
                "needs_review": needs_review,
                "evidence_grade": evidence_grade,
                "n": n_val,
                "source_url": source_url,
                "retrieved_on": "2026-10-11",
                "metric_definition": (
                    "O*NET 31.0 Interests and Work Context"
                    if tier == 2
                    else raw.get("metric_definition")
                ),
            }

            res = upsert(session, Occupation, {"name_en": name_en}, values)
            if res == "insert":
                inserts += 1
            else:
                updates += 1

            # Fetch committed occupation for ability foreign key
            occ_obj = session.query(Occupation).filter_by(name_en=name_en).first()
            if occ_obj and ability_vals:
                ab_key = {"occupation_id": occ_obj.id}
                ab_vals = {
                    "required_num": ability_vals["required_num"],
                    "required_verbal": ability_vals["required_verbal"],
                    "required_spatial": ability_vals["required_spatial"],
                    "required_mech": ability_vals["required_mech"],
                    "primary_ability": ability_vals["primary_ability"],
                    "source": "onet_abilities" if tier == 2 else "demo_synth_2026",
                    "source_year": 2026,
                    "is_demo": is_demo,
                    "needs_review": needs_review,
                    "evidence_grade": evidence_grade,
                    "n": n_val,
                    "source_url": source_url,
                    "retrieved_on": "2026-10-11",
                    "metric_definition": (
                        "O*NET 31.0 Abilities and Knowledge"
                        if tier == 2
                        else "Demo ability requirements"
                    ),
                }
                upsert(session, OccupationAbility, ab_key, ab_vals)
                abilities_upserted += 1

        session.commit()
    finally:
        session.close()

    total = inserts + updates
    pct_a = 100.0 * grade_a_count / total if total else 0.0
    print(
        f"build_occupation_master: {inserts} inserted, {updates} updated. "
        f"Grade A: {grade_a_count} ({pct_a:.1f}%), Grade D: {grade_d_count}. "
        f"Upserted {abilities_upserted} occupation_abilities records."
    )


if __name__ == "__main__":
    main()

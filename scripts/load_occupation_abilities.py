"""Load grounded occupation ability requirements into `occupation_abilities`.

Source: O*NET 31.0 Abilities and Knowledge (Grade A).
FK resolution: each CSV row names its occupation via `name_en`, which is looked up
in the already-built `occupations` table. Idempotent: keyed on `occupation_id`.

Run after build_occupation_master.py.
    python scripts/load_occupation_abilities.py
"""
from __future__ import annotations

import logging

from _common import SEED_DIR, read_csv, to_bool, to_float, to_int, upsert
from app.db.session import SessionLocal
from app.models import Occupation, OccupationAbility

logger = logging.getLogger(__name__)


def main(get_session=SessionLocal) -> None:
    csv_path = SEED_DIR / "occupation_abilities.csv"
    rows = read_csv(csv_path)
    if not rows:
        raise SystemExit(f"No occupation abilities rows found at {csv_path}")

    inserts = updates = missing = 0
    session = get_session()
    try:
        occ_cache: dict[str, int] = {}
        for raw in rows:
            name_en = raw["name_en"].strip()
            if name_en not in occ_cache:
                occ = session.query(Occupation).filter_by(name_en=name_en).one_or_none()
                occ_cache[name_en] = occ.id if occ else 0
            occupation_id = occ_cache[name_en]
            if not occupation_id:
                missing += 1
                logger.warning("No occupation found for ability row: %s", name_en)
                continue

            # Provenance & evidence integrity
            source = (raw.get("source") or "").strip()
            if not source:
                raise ValueError(f"DATA ADDENDUM Rule 1 violation: missing source for {name_en}")
            retrieved_on = (raw.get("retrieved_on") or "").strip()
            if not retrieved_on:
                msg = f"DATA ADDENDUM Rule 1 violation: missing retrieved_on for {name_en}"
                raise ValueError(msg)

            is_demo_val = to_bool(raw.get("is_demo"), default=False)
            evidence_grade = raw.get("evidence_grade") or ("D" if is_demo_val else "A")

            key = {"occupation_id": occupation_id}
            values = {
                "required_num": to_float(raw.get("required_num")) or 0.0,
                "required_verbal": to_float(raw.get("required_verbal")) or 0.0,
                "required_spatial": to_float(raw.get("required_spatial")) or 0.0,
                "required_mech": to_float(raw.get("required_mech")) or 0.0,
                "primary_ability": raw.get("primary_ability") or None,
                "source": source,
                "source_year": to_int(raw.get("source_year")),
                "is_demo": is_demo_val,
                "needs_review": to_bool(raw.get("needs_review")),
                "evidence_grade": evidence_grade,
                "retrieved_on": retrieved_on,
                "source_url": raw.get("source_url") or "https://www.onetcenter.org/database.html",
                "n": to_int(raw.get("n")),
                "metric_definition": raw.get("metric_definition") or None,
            }
            if upsert(session, OccupationAbility, key, values) == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    print(
        f"load_occupation_abilities: {inserts} inserted, {updates} updated "
        f"({missing} missing FKs) from {csv_path.name}"
    )


if __name__ == "__main__":
    main()

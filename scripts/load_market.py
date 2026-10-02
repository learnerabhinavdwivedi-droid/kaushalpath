"""Load market signals (salary / demand / placement) into the `market` table.

FK resolution: `occupation_name_en` locates the occupation. Idempotent: keyed on
(`occupation_id`, `state`, `year`).

Run after build_occupation_master.py.
    python scripts/load_market.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_float, to_int
from app.db.session import SessionLocal
from app.models import Market, Occupation


def main(get_session=SessionLocal) -> None:
    rows = read_csv(SEED_DIR / "market.csv")
    if not rows:
        raise SystemExit("No market rows found at backend/app/data/seed/market.csv")

    inserts = updates = missing = 0
    session = get_session()
    try:
        occ_cache: dict[str, int] = {}
        for raw in rows:
            occ_name = raw["occupation_name_en"].strip()
            if occ_name not in occ_cache:
                occ = session.query(Occupation).filter_by(name_en=occ_name).one_or_none()
                occ_cache[occ_name] = occ.id if occ else 0
            occupation_id = occ_cache[occ_name]
            if not occupation_id:
                missing += 1
                continue

            key = {
                "occupation_id": occupation_id,
                "state": raw["state"].strip(),
                "year": to_int(raw.get("year")),
            }
            values = {
                "avg_salary_inr": to_float(raw.get("avg_salary_inr")),
                "demand_index": to_float(raw.get("demand_index")),
                "placement_rate": to_float(raw.get("placement_rate")),
                "source": raw["source"].strip(),
                "source_year": to_int(raw.get("source_year")),
                "is_demo": to_bool(raw.get("is_demo"), default=True),
                "needs_review": to_bool(raw.get("needs_review")),
            }
            if _upsert(session, key, values) == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    print(f"load_market: {inserts} inserted, {updates} updated, {missing} unmatched")


def _upsert(session, key: dict, values: dict) -> str:
    obj = session.query(Market).filter_by(**key).one_or_none()
    if obj is None:
        session.add(Market(**key, **values))
        return "insert"
    for field, value in values.items():
        setattr(obj, field, value)
    return "update"


if __name__ == "__main__":
    main()

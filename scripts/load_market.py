"""Load market signals (salary / demand / placement) into the `market` table.

FK resolution: `occupation_name_en` locates the occupation. Idempotent: keyed on
(`occupation_id`, `state`, `year`).

Run after build_occupation_master.py.
    python scripts/load_market.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_float, to_int, upsert
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

            is_demo_val = to_bool(raw.get("is_demo"), default=True)
            key = {
                "occupation_id": occupation_id,
                "state": raw["state"].strip(),
                "district": (raw.get("district") or "").strip() or None,
                "year": to_int(raw.get("year")),
            }
            values = {
                "avg_salary_inr": to_float(raw.get("avg_salary_inr")),
                "earnings_p25": to_float(raw.get("earnings_p25")),
                "earnings_p75": to_float(raw.get("earnings_p75")),
                "demand_index": to_float(raw.get("demand_index")),
                "placement_rate": to_float(raw.get("placement_rate")),
                "source": raw["source"].strip(),
                "source_year": to_int(raw.get("source_year")),
                "is_demo": is_demo_val,
                "needs_review": to_bool(raw.get("needs_review")),
                "evidence_grade": raw.get("evidence_grade") or ("D" if is_demo_val else "C"),
                "retrieved_on": raw.get("retrieved_on") or "2026-10-11",
                "source_url": raw.get("source_url") or "local://backend/app/data/seed/market.csv",
                "n": to_int(raw.get("n")),
                "metric_definition": raw.get("metric_definition") or None,
            }
            if upsert(session, Market, key, values) == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    print(f"load_market: {inserts} inserted, {updates} updated, {missing} unmatched")



if __name__ == "__main__":
    main()

"""Load government schemes into `schemes` table.

Idempotent: keyed on (`name`).
Run after build_occupation_master.py.
    python scripts/load_schemes.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_int
from app.db.session import SessionLocal
from app.models import Scheme


def main(get_session=SessionLocal) -> None:
    csv_path = SEED_DIR / "schemes.csv"
    if not csv_path.exists():
        print("load_schemes: no schemes.csv found, skipping")
        return

    rows = read_csv(csv_path)
    if not rows:
        print("load_schemes: empty schemes.csv, skipping")
        return

    inserts = updates = 0
    session = get_session()
    try:
        for raw in rows:
            name = raw["name"].strip()
            key = {"name": name}
            values = {
                "benefit_text_en": raw["benefit_text_en"].strip(),
                "benefit_text_hi": raw["benefit_text_hi"].strip(),
                "eligibility_text": (raw.get("eligibility_text") or "").strip() or None,
                "url": (raw.get("url") or "").strip() or None,
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

    print(f"load_schemes: {inserts} inserted, {updates} updated")


def _upsert(session, key: dict, values: dict) -> str:
    obj = session.query(Scheme).filter_by(**key).one_or_none()
    if obj is None:
        session.add(Scheme(**key, **values))
        return "insert"
    for field, value in values.items():
        setattr(obj, field, value)
    return "update"


if __name__ == "__main__":
    main()

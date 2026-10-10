"""Load training centres into the `centres` table.

FK resolution: `occupation_name_en` + `course_name` locate a `courses` row.
Idempotent: keyed on (`course_id`, `name`, `district`).

Run after load_courses.py.
    python scripts/load_centres.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_float, to_int, upsert
from app.db.session import SessionLocal
from app.models import Centre, Course, Occupation


def main(get_session=SessionLocal) -> None:
    rows = read_csv(SEED_DIR / "centres.csv")
    if not rows:
        raise SystemExit("No centre rows found at backend/app/data/seed/centres.csv")

    inserts = updates = missing = 0
    session = get_session()
    try:
        for raw in rows:
            occ_name = raw["occupation_name_en"].strip()
            course_name = raw["course_name"].strip()
            occ = session.query(Occupation).filter_by(name_en=occ_name).one_or_none()
            course = None
            if occ:
                course = (
                    session.query(Course)
                    .filter_by(occupation_id=occ.id, name=course_name)
                    .one_or_none()
                )
            if not course:
                missing += 1
                continue

            is_demo_val = to_bool(raw.get("is_demo"), default=True)
            key = {
                "course_id": course.id,
                "name": raw["name"].strip(),
                "district": raw["district"].strip(),
            }
            values = {
                "state": raw["state"].strip(),
                "lat": to_float(raw.get("lat")),
                "lon": to_float(raw.get("lon")),
                "source": raw["source"].strip(),
                "source_year": int(raw["source_year"]) if raw.get("source_year") else None,
                "is_demo": is_demo_val,
                "needs_review": to_bool(raw.get("needs_review")),
                "provider_type": (raw.get("provider_type") or "").strip() or None,
                "affiliation": (raw.get("affiliation") or "").strip() or None,
                "has_female_trainers": to_bool(raw.get("has_female_trainers"), default=False),
                "has_hostel": to_bool(raw.get("has_hostel"), default=False),
                "transport_note": (raw.get("transport_note") or "").strip() or None,
                "safety_certified": to_bool(raw.get("safety_certified"), default=False),
                "evidence_grade": raw.get("evidence_grade") or ("D" if is_demo_val else "A"),
                "retrieved_on": raw.get("retrieved_on") or "2026-10-11",
                "source_url": raw.get("source_url") or "local://backend/app/data/seed/centres.csv",
                "n": to_int(raw.get("n")),
                "metric_definition": raw.get("metric_definition") or None,
            }
            if upsert(session, Centre, key, values) == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    print(f"load_centres: {inserts} inserted, {updates} updated, {missing} unmatched")



if __name__ == "__main__":
    main()

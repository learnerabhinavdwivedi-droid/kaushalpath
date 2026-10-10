"""Load provider outcomes into `provider_outcomes` table.

FK resolution:
  - (provider_name, district) -> centres.id
  - course_name -> courses.id

Idempotent: keyed on (`provider_id`, `course_id`, `cohort_year`).
Run after load_centres.py.
    python scripts/load_provider_outcomes.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_float, to_int, upsert
from app.db.session import SessionLocal
from app.models import Centre, Course, ProviderOutcome


def main(get_session=SessionLocal) -> None:
    csv_path = SEED_DIR / "provider_outcomes.csv"
    if not csv_path.exists():
        print("load_provider_outcomes: no provider_outcomes.csv found, skipping")
        return

    rows = read_csv(csv_path)
    if not rows:
        print("load_provider_outcomes: empty provider_outcomes.csv, skipping")
        return

    inserts = updates = missing = 0
    session = get_session()
    try:
        centre_cache: dict[tuple[str, str], int] = {}
        course_cache: dict[str, int] = {}

        for raw in rows:
            prov_name = raw["provider_name"].strip()
            district = raw["district"].strip()
            c_key = (prov_name, district)
            if c_key not in centre_cache:
                c = session.query(Centre).filter_by(name=prov_name, district=district).first()
                centre_cache[c_key] = c.id if c else 0
            provider_id = centre_cache[c_key]

            course_name = raw["course_name"].strip()
            if course_name not in course_cache:
                cr = session.query(Course).filter_by(name=course_name).first()
                course_cache[course_name] = cr.id if cr else 0
            course_id = course_cache[course_name]

            if not provider_id or not course_id:
                missing += 1
                continue

            cohort_year = to_int(raw.get("cohort_year"))
            is_demo_val = to_bool(raw.get("is_demo"), default=True)
            key = {
                "provider_id": provider_id,
                "course_id": course_id,
                "cohort_year": cohort_year,
            }
            certified_val = to_int(raw.get("certified"))
            values = {
                "enrolled": to_int(raw.get("enrolled")),
                "certified": certified_val,
                "placed": to_int(raw.get("placed")),
                "placement_rate": to_float(raw.get("placement_rate")),
                "earnings_p25": to_float(raw.get("earnings_p25")),
                "earnings_median": to_float(raw.get("earnings_median")),
                "earnings_p75": to_float(raw.get("earnings_p75")),
                "self_employed_pct": to_float(raw.get("self_employed_pct")),
                "apprenticeship_stipend_inr": to_float(raw.get("apprenticeship_stipend_inr")),
                "source": raw["source"].strip(),
                "source_year": to_int(raw.get("source_year")),
                "is_demo": is_demo_val,
                "needs_review": to_bool(raw.get("needs_review")),
                "evidence_grade": raw.get("evidence_grade")
                or ("D" if is_demo_val else "B"),
                "retrieved_on": raw.get("retrieved_on") or "2026-10-11",
                "source_url": raw.get("source_url")
                or "local://backend/app/data/seed/provider_outcomes.csv",
                "n": to_int(raw.get("n")) or certified_val,
                "metric_definition": raw.get("metric_definition")
                or "Post-placement tracking outcome",
            }
            if upsert(session, ProviderOutcome, key, values) == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    print(f"load_provider_outcomes: {inserts} inserted, {updates} updated, {missing} unmatched")



if __name__ == "__main__":
    main()

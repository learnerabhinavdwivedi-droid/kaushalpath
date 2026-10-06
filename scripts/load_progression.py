"""Load progression pathways into `progression_paths` table.

FK resolution:
  - course_name -> courses.id (from_course_id)
  - to_course_name -> courses.id (to_course_id, optional)

Idempotent: keyed on (`from_course_id`, `to_label`).
Run after load_courses.py.
    python scripts/load_progression.py
"""
from __future__ import annotations

from _common import SEED_DIR, read_csv, to_bool, to_int
from app.db.session import SessionLocal
from app.models import Course, ProgressionPath


def main(get_session=SessionLocal) -> None:
    csv_path = SEED_DIR / "progression_paths.csv"
    if not csv_path.exists():
        print("load_progression: no progression_paths.csv found, skipping")
        return

    rows = read_csv(csv_path)
    if not rows:
        print("load_progression: empty progression_paths.csv, skipping")
        return

    inserts = updates = missing = 0
    session = get_session()
    try:
        course_cache: dict[str, int] = {}

        for raw in rows:
            course_name = raw["course_name"].strip()
            if course_name not in course_cache:
                cr = session.query(Course).filter_by(name=course_name).first()
                course_cache[course_name] = cr.id if cr else 0
            from_course_id = course_cache[course_name]

            if not from_course_id:
                missing += 1
                continue

            to_course_name = (raw.get("to_course_name") or "").strip()
            to_course_id = None
            if to_course_name:
                if to_course_name not in course_cache:
                    t_cr = session.query(Course).filter_by(name=to_course_name).first()
                    course_cache[to_course_name] = t_cr.id if t_cr else 0
                to_course_id = course_cache[to_course_name] or None

            to_label = raw["to_label"].strip()
            key = {
                "from_course_id": from_course_id,
                "to_label": to_label,
            }
            values = {
                "to_course_id": to_course_id,
                "kind": raw["kind"].strip(),
                "credit_note": (raw.get("credit_note") or "").strip() or None,
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

    print(f"load_progression: {inserts} inserted, {updates} updated, {missing} unmatched")


def _upsert(session, key: dict, values: dict) -> str:
    obj = session.query(ProgressionPath).filter_by(**key).one_or_none()
    if obj is None:
        session.add(ProgressionPath(**key, **values))
        return "insert"
    for field, value in values.items():
        setattr(obj, field, value)
    return "update"


if __name__ == "__main__":
    main()

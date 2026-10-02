"""Phase 1 data quality report.

Prints: row counts, null %, duplicate %, rows per source, % is_demo, occupation
coverage by NSQF level, and coverage by state (from centres + market). Read-only.

Run: python scripts/data_report.py
"""
from __future__ import annotations

from _common import BACKEND_DIR  # noqa: F401  (ensures sys.path bootstrap)
from app.db.session import SessionLocal
from app.models import Centre, Course, Market, Occupation
from sqlalchemy import func

TABLES = {
    "occupations": (Occupation, ["name_en", "name_hi", "nsqf_level", "source"]),
    "courses": (Course, ["occupation_id", "name", "nsqf_level", "fee_inr", "source"]),
    "centres": (Centre, ["course_id", "name", "district", "state", "source"]),
    "market": (
        Market,
        ["occupation_id", "state", "avg_salary_inr", "demand_index", "placement_rate", "source"],
    ),
}


def _null_pct(session, model, col) -> float:
    total = session.query(func.count(model.id)).scalar() or 0
    if not total:
        return 0.0
    nulls = session.query(func.count(model.id)).filter(col.is_(None)).scalar() or 0
    return 100.0 * nulls / total


def _table_report(session, name: str, model, key_cols: list[str]) -> None:
    total = session.query(func.count(model.id)).scalar() or 0
    print(f"\n== {name} ({total} rows) ==")
    for col_name in key_cols:
        col = getattr(model, col_name)
        print(f"  null% {col_name:<16} {_null_pct(session, model, col):5.1f}")

    demo = session.query(func.count(model.id)).filter(model.is_demo.is_(True)).scalar() or 0
    demo_pct = 100.0 * demo / total if total else 0.0
    print(f"  % is_demo          {demo_pct:5.1f}")

    print("  rows per source:")
    for source, cnt in session.query(model.source, func.count(model.id)).group_by(
        model.source
    ).all():
        print(f"    {source or '(none)':<20} {cnt}")

    # duplicate % on the model's natural key columns
    print(f"  duplicates by {name} natural key: {_dup_pct(session, model, name)}")


def _dup_pct(session, model, name: str) -> float:
    if name == "occupations":
        cols = [model.name_en]
    elif name == "courses":
        cols = [model.occupation_id, model.name]
    elif name == "centres":
        cols = [model.course_id, model.name, model.district]
    else:  # market
        cols = [model.occupation_id, model.state, model.year]
    total = session.query(func.count(model.id)).scalar() or 0
    if not total:
        return 0.0
    distinct = session.query(func.count()).select_from(
        session.query(*cols).group_by(*cols).subquery()
    ).scalar() or 0
    return 100.0 * (total - distinct) / total


def _coverage(session) -> None:
    print("\n== occupation coverage ==")
    total_occ = session.query(func.count(Occupation.id)).scalar() or 0
    print(f"  total occupations: {total_occ}")

    print("  by NSQF level:")
    for level, cnt in session.query(Occupation.nsqf_level, func.count(Occupation.id)).group_by(
        Occupation.nsqf_level
    ).order_by(Occupation.nsqf_level).all():
        print(f"    level {str(level or '(unset)'):<10} {cnt}")

    occ_with_hi = session.query(func.count(Occupation.id)).filter(
        Occupation.name_hi.isnot(None)
    ).scalar() or 0
    occ_with_riasec = session.query(func.count(Occupation.id)).filter(
        (Occupation.riasec_r + Occupation.riasec_i + Occupation.riasec_a
         + Occupation.riasec_s + Occupation.riasec_e + Occupation.riasec_c)
        > 0
    ).scalar() or 0
    print(f"  occupations with Hindi name: {occ_with_hi}/{total_occ}")
    print(f"  occupations with RIASEC vector: {occ_with_riasec}/{total_occ}")

    states = set()
    for (state,) in session.query(Centre.state).distinct().all():
        states.add(state)
    for (state,) in session.query(Market.state).distinct().all():
        states.add(state)
    print(f"  distinct states covered (centres+market): {len(states)}")

    mk_total = session.query(func.count(Market.id)).scalar() or 0
    mk_with_rate = session.query(func.count(Market.id)).filter(
        Market.placement_rate.isnot(None)
    ).scalar() or 0
    print(f"  market rows with placement_rate: {mk_with_rate}/{mk_total}")


def main() -> None:
    session = SessionLocal()
    try:
        for name, (model, key_cols) in TABLES.items():
            _table_report(session, name, model, key_cols)
        _coverage(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()

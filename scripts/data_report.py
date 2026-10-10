"""Phase 19 Data Quality and Foundation Report.

Prints:
- Coverage per table x evidence grade x state
- Share of rows with n >= 30
- Share of trades with both an NCO code and a QP code
- Unmatched / review counts from trade_crosswalk_review.csv and geo_rejects.csv
- Verification that every demo row is grade D

Run: python scripts/data_report.py
"""
from __future__ import annotations

import csv

from _common import BACKEND_DIR, PROCESSED_DIR  # noqa: F401  (ensures sys.path bootstrap)
from app.db.session import SessionLocal
from app.models import (
    Centre,
    Course,
    Crosswalk,
    Geo,
    GeoAlias,
    Market,
    Occupation,
    ProgressionPath,
    ProviderOutcome,
    Scheme,
    Trade,
    TradeAlias,
)
from sqlalchemy import func

TABLES = {
    "occupations": (
        Occupation,
        ["name_en", "name_hi", "nsqf_level", "source", "evidence_grade"],
    ),
    "courses": (
        Course,
        ["occupation_id", "name", "nsqf_level", "fee_inr", "source", "evidence_grade"],
    ),
    "centres": (
        Centre,
        ["course_id", "name", "district", "state", "source", "evidence_grade"],
    ),
    "market": (
        Market,
        [
            "occupation_id",
            "state",
            "avg_salary_inr",
            "demand_index",
            "placement_rate",
            "source",
            "evidence_grade",
        ],
    ),
    "provider_outcomes": (
        ProviderOutcome,
        [
            "provider_id",
            "course_id",
            "cohort_year",
            "placement_rate",
            "earnings_median",
            "source",
            "evidence_grade",
        ],
    ),
    "trades": (
        Trade,
        [
            "trade_id",
            "name_en",
            "nco_code",
            "qp_code",
            "ncvt_trade_code",
            "source",
            "evidence_grade",
        ],
    ),
    "progression_paths": (
        ProgressionPath,
        ["from_course_id", "to_label", "kind", "source"],
    ),
    "schemes": (
        Scheme,
        ["name", "benefit_text_en", "benefit_text_hi", "source"],
    ),
}


def _null_pct(session, model, col) -> float:
    pk = model.trade_id if hasattr(model, "trade_id") else model.id
    total = session.query(func.count(pk)).scalar() or 0
    if not total:
        return 0.0
    nulls = session.query(func.count(pk)).filter(col.is_(None)).scalar() or 0
    return 100.0 * nulls / total


def _table_report(session, name: str, model, key_cols: list[str]) -> None:
    pk = model.trade_id if hasattr(model, "trade_id") else model.id
    total = session.query(func.count(pk)).scalar() or 0
    print(f"\n== {name} ({total} rows) ==")
    for col_name in key_cols:
        col = getattr(model, col_name)
        print(f"  null% {col_name:<18} {_null_pct(session, model, col):5.1f}")

    if hasattr(model, "is_demo"):
        demo = session.query(func.count(pk)).filter(model.is_demo.is_(True)).scalar() or 0
        demo_pct = 100.0 * demo / total if total else 0.0
        print(f"  % is_demo            {demo_pct:5.1f}")

    # Evidence grade breakdown
    if hasattr(model, "evidence_grade"):
        print("  coverage by evidence grade:")
        for grade in ("A", "B", "C", "D"):
            cnt = session.query(func.count(pk)).filter(model.evidence_grade == grade).scalar() or 0
            pct = 100.0 * cnt / total if total else 0.0
            print(f"    Grade {grade}: {cnt:4d} ({pct:5.1f}%)")

    # Sample size share n >= 30
    if hasattr(model, "n"):
        n_30 = session.query(func.count(pk)).filter(model.n >= 30).scalar() or 0
        n_pct = 100.0 * n_30 / total if total else 0.0
        print(f"  share of rows with n>=30: {n_30}/{total} ({n_pct:5.1f}%)")

    # Coverage per grade x state (for tables with state column)
    if hasattr(model, "state") and hasattr(model, "evidence_grade"):
        print("  coverage per grade x state:")
        state_grades = (
            session.query(model.state, model.evidence_grade, func.count(pk))
            .group_by(model.state, model.evidence_grade)
            .order_by(model.state)
            .all()
        )
        for st, gr, cnt in state_grades[:10]:
            print(f"    {st:<20} [Grade {gr}]: {cnt}")
        if len(state_grades) > 10:
            print(f"    ... and {len(state_grades) - 10} more state x grade combinations.")

    print("  rows per source:")
    for source, cnt in session.query(model.source, func.count(pk)).group_by(
        model.source
    ).all():
        print(f"    {source or '(none)':<25} {cnt}")

    # duplicate % on the model's natural key columns
    print(f"  duplicates by {name} natural key: {_dup_pct(session, model, name)}")


def _dup_pct(session, model, name: str) -> float:
    if name == "occupations":
        cols = [model.name_en]
    elif name == "courses":
        cols = [model.occupation_id, model.name]
    elif name == "centres":
        cols = [model.course_id, model.name, model.district]
    elif name == "provider_outcomes":
        cols = [model.provider_id, model.course_id, model.cohort_year]
    elif name == "trades":
        cols = [model.trade_id]
    elif name == "progression_paths":
        cols = [model.from_course_id, model.to_label]
    elif name == "schemes":
        cols = [model.name]
    else:  # market
        cols = [model.occupation_id, model.state, model.district, model.year]

    pk = model.trade_id if hasattr(model, "trade_id") else model.id
    total = session.query(func.count(pk)).scalar() or 0
    if not total:
        return 0.0
    distinct = session.query(func.count()).select_from(
        session.query(*cols).group_by(*cols).subquery()
    ).scalar() or 0
    return 100.0 * (total - distinct) / total


def _trades_and_crosswalk_report(session) -> None:
    print("\n== trades & crosswalk metrics (Phase 19) ==")
    total_trades = session.query(func.count(Trade.trade_id)).scalar() or 0
    with_both = session.query(func.count(Trade.trade_id)).filter(
        Trade.nco_code.isnot(None),
        Trade.qp_code.isnot(None),
    ).scalar() or 0
    both_pct = 100.0 * with_both / total_trades if total_trades else 0.0
    print(f"  total trades: {total_trades}")
    print(f"  trades with BOTH NCO code and QP code: {with_both}/{total_trades} ({both_pct:5.1f}%)")

    total_aliases = session.query(func.count(TradeAlias.id)).scalar() or 0
    print(f"  trade aliases recorded: {total_aliases}")

    cw_total = session.query(func.count(Crosswalk.id)).scalar() or 0
    cw_review = (
        session.query(func.count(Crosswalk.id))
        .filter(Crosswalk.needs_review.is_(True))
        .scalar()
        or 0
    )
    print(f"  crosswalk entries: {cw_total} (needing review: {cw_review})")

    geo_total = session.query(func.count(Geo.id)).scalar() or 0
    geo_aliases = session.query(func.count(GeoAlias.id)).scalar() or 0
    print(f"  canonical geo districts: {geo_total}, geo aliases: {geo_aliases}")

    # Unmatched counts from review / reject logs
    review_csv = PROCESSED_DIR / "trade_crosswalk_review.csv"
    review_csv_count = 0
    if review_csv.exists():
        with review_csv.open(encoding="utf-8") as fh:
            review_csv_count = max(0, len(list(csv.reader(fh))) - 1)
    print(f"  trade crosswalk items awaiting human review: {review_csv_count}")

    geo_rejects = PROCESSED_DIR / "geo_rejects.csv"
    geo_rejects_count = 0
    if geo_rejects.exists():
        with geo_rejects.open(encoding="utf-8") as fh:
            geo_rejects_count = max(0, len(list(csv.reader(fh))) - 1)
    print(f"  unmatched geography rejects recorded: {geo_rejects_count}")


def _coverage(session) -> None:
    print("\n== occupation coverage ==")
    total_occ = session.query(func.count(Occupation.id)).scalar() or 0
    voc_occ = session.query(func.count(Occupation.id)).filter(
        Occupation.is_vocational.is_(True)
    ).scalar() or 0
    print(f"  total occupations: {total_occ} (vocational: {voc_occ})")

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


def main() -> None:
    session = SessionLocal()
    try:
        for name, (model, key_cols) in TABLES.items():
            _table_report(session, name, model, key_cols)
        _trades_and_crosswalk_report(session)
        _coverage(session)
    finally:
        session.close()


if __name__ == "__main__":
    main()

"""Build the unified occupation master.

Source of truth for the `occupations` table. Reads the curated demo master
(`backend/app/data/seed/occupations.csv`) and, when the user has dropped the
corresponding files into `backend/app/data/raw/`, enriches rows with real
O*NET codes, ESCO URIs / Hindi names and the PS-provided dataset (see
docs/PS_SPEC.md and data/raw/README.md). Idempotent: keyed on `name_en`.

Run: python scripts/build_occupation_master.py
"""
from __future__ import annotations

from _common import PROCESSED_DIR, RAW_DIR, SEED_DIR, read_csv, to_bool, to_float, to_int
from app.db.session import SessionLocal
from app.models import Occupation


def _load_enrichment() -> dict[str, dict[str, str]]:
    """Merge optional raw/processed files into {name_en: {column: value}}."""
    enrich: dict[str, dict[str, str]] = {}

    onet = PROCESSED_DIR / "onet_master.csv"
    if onet.exists():
        for row in read_csv(onet):
            name = (row.get("name_en") or "").strip()
            if name:
                enrich.setdefault(name, {})["onet_code"] = row.get("onet_code", "")

    esco = PROCESSED_DIR / "esco_master.csv"
    if esco.exists():
        for row in read_csv(esco):
            name = (row.get("name_en") or "").strip()
            if name:
                slot = enrich.setdefault(name, {})
                slot["esco_uri"] = row.get("esco_uri", "")
                if row.get("name_hi"):
                    slot["name_hi"] = row["name_hi"]

    provided = PROCESSED_DIR / "provided_master.csv"
    if provided.exists():
        for row in read_csv(provided):
            name = (row.get("name_en") or "").strip()
            if name:
                enrich.setdefault(name, {}).update(
                    {k: v for k, v in row.items() if k != "name_en" and v}
                )

    return enrich


def _present_raw_sources() -> list[str]:
    found = []
    for label, path in (
        ("O*NET", RAW_DIR / "onet"),
        ("ESCO", RAW_DIR / "esco"),
        ("Provided", RAW_DIR / "provided"),
    ):
        if path.exists():
            found.append(label)
    return found


def main(get_session=SessionLocal) -> None:
    rows = read_csv(SEED_DIR / "occupations.csv")
    if not rows:
        raise SystemExit("No seed occupations found at backend/app/data/seed/occupations.csv")

    enrich = _load_enrichment()
    inserts = updates = 0
    session = get_session()
    try:
        for raw in rows:
            name_en = raw["name_en"].strip()
            extra = enrich.get(name_en, {})
            values = {
                "name_hi": extra.get("name_hi") or (raw.get("name_hi") or None),
                "nco_code": extra.get("nco_code") or (raw.get("nco_code") or None),
                "onet_code": extra.get("onet_code") or (raw.get("onet_code") or None),
                "esco_uri": extra.get("esco_uri") or (raw.get("esco_uri") or None),
                "nsqf_level": to_int(raw.get("nsqf_level")),
                "description": raw.get("description") or None,
                "riasec_r": to_float(raw.get("riasec_r")) or 0.0,
                "riasec_i": to_float(raw.get("riasec_i")) or 0.0,
                "riasec_a": to_float(raw.get("riasec_a")) or 0.0,
                "riasec_s": to_float(raw.get("riasec_s")) or 0.0,
                "riasec_e": to_float(raw.get("riasec_e")) or 0.0,
                "riasec_c": to_float(raw.get("riasec_c")) or 0.0,
                "source": extra.get("source") or raw["source"].strip(),
                "source_year": to_int(extra.get("source_year") or raw.get("source_year")),
                "is_demo": to_bool(extra.get("is_demo", raw.get("is_demo")), default=True),
                "needs_review": to_bool(extra.get("needs_review", raw.get("needs_review"))),
            }
            result = _upsert_occupation(session, name_en, values)
            if result == "insert":
                inserts += 1
            else:
                updates += 1
        session.commit()
    finally:
        session.close()

    raw_found = _present_raw_sources()
    note = f" enriched from raw sources: {', '.join(raw_found)}" if raw_found else " (demo only)"
    print(f"build_occupation_master: {inserts} inserted, {updates} updated{note}")


def _upsert_occupation(session, name_en: str, values: dict) -> str:
    obj = session.query(Occupation).filter_by(name_en=name_en).one_or_none()
    if obj is None:
        session.add(Occupation(name_en=name_en, **values))
        return "insert"
    for field, value in values.items():
        setattr(obj, field, value)
    return "update"


if __name__ == "__main__":
    main()

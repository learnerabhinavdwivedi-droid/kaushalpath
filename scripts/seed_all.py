"""Run the full Phase 1 seed pipeline in dependency order.

Creates the schema if it is not present (dev convenience — production uses
`alembic upgrade head`), then runs the loaders. Safe to run repeatedly: every
loader upserts by natural key, so row counts stay stable. This is what `make
seed` invokes.

Run: python scripts/seed_all.py
"""
from __future__ import annotations

import _common  # noqa: F401  # bootstraps sys.path so app.* + loader imports resolve
import app.models  # noqa: F401  # register all tables on Base.metadata
import build_occupation_master
import build_retrieval_index
import load_centres
import load_courses
import load_esco
import load_market
import load_onet
import load_progression
import load_provided_dataset
import load_provider_outcomes
import load_schemes
from app.db import Base, engine


def main() -> None:
    Base.metadata.create_all(bind=engine)

    # Optional real-data ingestion first (no-ops with a TODO if raw/ is empty).
    load_onet.main()
    load_esco.main()
    load_provided_dataset.main()

    # Demo + merged reference data.
    build_occupation_master.main()
    load_courses.main()
    load_centres.main()
    load_market.main()
    load_provider_outcomes.main()
    load_progression.main()
    load_schemes.main()

    # Phase 19 Data Foundation: canonical LGD geo and trade resolution
    import resolve_trades
    from app.db.session import SessionLocal
    from app.services import geo_svc

    session = SessionLocal()
    try:
        geo_count, alias_count = geo_svc.seed_canonical_geo(session)
        print(f"seed_all: seeded {geo_count} canonical geo districts, {alias_count} geo aliases")
    finally:
        session.close()

    resolve_trades.main()

    # Retrieval artefact for Phase 3 (no-ops if the embedding stack is absent).
    build_retrieval_index.main()

    print("seed_all: done")


if __name__ == "__main__":
    main()

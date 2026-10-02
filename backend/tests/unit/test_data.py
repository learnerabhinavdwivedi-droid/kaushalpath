"""Phase 1 data-layer tests (selected with `pytest -k data`).

Covers: the Alembic initial migration round-trips, the loaders are idempotent
(run twice -> same counts) and produce >=150 sourced occupations, and the model
CHECK/UNIQUE constraints are enforced. All run against throwaway SQLite files so
the dev database is never touched.
"""
from __future__ import annotations

import sqlite3
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.db.base import Base
from app.models import Course, Market, Occupation, User

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = BACKEND_DIR.parent / "scripts"

# make the loader scripts importable (they are not a package)
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import build_occupation_master  # noqa: E402
import load_centres  # noqa: E402
import load_courses  # noqa: E402
import load_market  # noqa: E402


@pytest.fixture()
def db_session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(f"sqlite:///{tmp_path / 'data.db'}", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def session_factory(tmp_path: Path):
    engine = create_engine(f"sqlite:///{tmp_path / 'load.db'}", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, expire_on_commit=False, future=True)


# --- migration ---------------------------------------------------------------
def test_data_migration_up_and_down(tmp_path: Path) -> None:
    from alembic import command
    from alembic.config import Config

    db_file = tmp_path / "migration.db"
    old = __import__("os").environ.get("DATABASE_URL")
    __import__("os").environ["DATABASE_URL"] = f"sqlite:///{db_file}"
    get_settings.cache_clear()
    try:
        cfg = Config(str(BACKEND_DIR / "alembic.ini"))
        cfg.set_main_option("script_location", str(BACKEND_DIR / "app" / "db" / "migrations"))

        command.upgrade(cfg, "head")
        tables = _sqlite_tables(db_file)
        assert {"users", "occupations", "courses", "centres", "market", "votes"} <= tables

        command.downgrade(cfg, "base")
        remaining = _sqlite_tables(db_file)
        assert "occupations" not in remaining
    finally:
        if old is None:
            __import__("os").environ.pop("DATABASE_URL", None)
        else:
            __import__("os").environ["DATABASE_URL"] = old
        get_settings.cache_clear()


def _sqlite_tables(path: Path) -> set[str]:
    con = sqlite3.connect(path)
    try:
        return {row[0] for row in con.execute("select name from sqlite_master where type='table'")}
    finally:
        con.close()


# --- loader idempotency ------------------------------------------------------
def test_data_loaders_are_idempotent(session_factory) -> None:
    build_occupation_master.main(get_session=session_factory)
    load_courses.main(get_session=session_factory)
    load_centres.main(get_session=session_factory)
    load_market.main(get_session=session_factory)

    occ_count = _count(session_factory, Occupation)
    course_count = _count(session_factory, Course)
    assert occ_count >= 150, "occupation master must include at least 150 rows"

    # second run must not change any count
    build_occupation_master.main(get_session=session_factory)
    load_courses.main(get_session=session_factory)
    load_centres.main(get_session=session_factory)
    load_market.main(get_session=session_factory)

    assert _count(session_factory, Occupation) == occ_count
    assert _count(session_factory, Course) == course_count
    assert occ_count > 0


def _count(session_factory, model) -> int:
    s = session_factory()
    try:
        return s.query(model).count()
    finally:
        s.close()


def test_data_every_occupation_has_source(session_factory) -> None:
    build_occupation_master.main(get_session=session_factory)
    s = session_factory()
    try:
        missing = s.query(Occupation).filter(
            (Occupation.source.is_(None)) | (Occupation.source == "")
        ).count()
        assert missing == 0, "RULES: every data row must carry a source"
    finally:
        s.close()


def test_data_market_has_placement_rate(session_factory) -> None:
    build_occupation_master.main(get_session=session_factory)
    load_market.main(get_session=session_factory)
    s = session_factory()
    try:
        total = s.query(Market).count()
        with_rate = s.query(Market).filter(Market.placement_rate.isnot(None)).count()
        assert total > 0, "market seed must load rows"
        assert with_rate == total, "PS 26241: every market row must carry placement_rate"
    finally:
        s.close()


# --- constraints -------------------------------------------------------------
def test_data_user_role_check_constraint(db_session: Session) -> None:
    db_session.add(User(email="ok@x.com", hashed_password="x", role="student"))
    db_session.commit()
    db_session.add(User(email="bad@x.com", hashed_password="x", role="hacker"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_data_occupation_name_en_unique(db_session: Session) -> None:
    db_session.add(Occupation(name_en="Fitter", source="demo_synth_2026"))
    db_session.commit()
    db_session.add(Occupation(name_en="Fitter", source="demo_synth_2026"))
    with pytest.raises(IntegrityError):
        db_session.commit()

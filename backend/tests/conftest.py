"""Shared test fixtures.

`app.dependency_overrides` is a single global dict on the FastAPI app. When one
test file sets it at import time and another calls `.clear()` at teardown, they
silently clobber each other and the suite becomes order-dependent. The fixtures
here make override ownership explicit and always restore the prior state, so
each test is isolated regardless of execution order.
"""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.ml.ranking.ranker import Ranker


@pytest.fixture(autouse=True)
def _disable_rate_limit():
    """Keep slowapi throttling out of the test-suite.

    Every TestClient request shares one remote address, so the auth rate limits
    (a real prod control) would otherwise fail unrelated tests. Toggle the
    limiter off per test and restore it afterwards.
    """
    from app.core.rate_limit import limiter

    limiter.enabled = False
    yield
    limiter.enabled = True


@pytest.fixture(autouse=True)
def _deterministic_ranker(monkeypatch):
    """Force the transparent fallback scorer for every test.

    A trained `ranker_model.txt` is a dev/eval artefact, not part of the repo;
    tests must be reproducible whether or not one happens to sit on disk, so we
    make `Ranker()` never load it (the fallback is the documented default).
    """
    orig_init = Ranker.__init__

    def _init(self, use_model: bool = False):
        orig_init(self, use_model=False)

    monkeypatch.setattr(Ranker, "__init__", _init)


@pytest.fixture()
def db_session():
    """A fresh in-memory SQLite schema + session per test (no shared dev DB)."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as session:
        yield session
    engine.dispose()


@pytest.fixture()
def client_with_db(db_session):
    """A TestClient whose `get_db` yields `db_session`, with clean teardown."""
    saved = dict(app.dependency_overrides)

    def _override():
        yield db_session

    app.dependency_overrides[get_db] = _override
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    app.dependency_overrides.update(saved)

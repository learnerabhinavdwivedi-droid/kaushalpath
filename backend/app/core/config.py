"""Application configuration.

All settings are read from the environment / `.env` (pydantic-settings).
No hard-coded secrets — see `.env.example`. Defaults are dev-safe so the
test-suite and `make check` run without a populated `.env`.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Backend directory (…/kaushalpath/backend) — the anchor for the dev SQLite file.
_BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    # App
    app_name: str = "KaushalPath"
    app_env: str = "dev"  # dev | test | prod
    debug: bool = True
    log_level: str = "INFO"

    # Security — MUST be overridden via .env in prod (RULES: no hard-coded secrets)
    secret_key: str = "dev-only-insecure-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    # slowapi rate limiting on auth endpoints. Tests force this off via conftest.
    rate_limit_enabled: bool = True

    # Database (SQLite for dev per docs/02_ARCHITECTURE.md)
    database_url: str = "sqlite:///./kaushalpath.db"

    @model_validator(mode="after")
    def _anchor_sqlite_path(self) -> Settings:
        """Pin a *relative* file-backed SQLite URL to the backend dir.

        `sqlite:///./x.db` resolves against the process CWD, so seeding from the
        repo root (`python scripts/seed_all.py`) and reading from the app
        (`uvicorn --app-dir backend`) would otherwise open two different files.
        Absolute paths and `:memory:` are left untouched (tests rely on those).
        """
        prefix = "sqlite:///"
        url = self.database_url
        if url.startswith(prefix) and ":memory:" not in url:
            raw = url[len(prefix):]
            if not os.path.isabs(raw):
                resolved = (_BACKEND_DIR / raw).resolve()
                self.database_url = f"{prefix}{resolved}"
        return self

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:5173"

    # ML Models
    embedder_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    model_version: str = "kaushalpath-rank-0.1.0"

    # Fallback ranker weights (used when the LightGBM model is not trained)
    ranker_weight_riasec: float = 0.35
    ranker_weight_overlap: float = 0.10
    ranker_weight_aptitude: float = 0.15
    ranker_weight_demand: float = 0.10
    ranker_weight_salary: float = 0.05
    ranker_weight_retrieval: float = 0.20
    ranker_weight_fee: float = 0.10
    ranker_weight_nsqf: float = 0.05
    ranker_weight_distance: float = 0.10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

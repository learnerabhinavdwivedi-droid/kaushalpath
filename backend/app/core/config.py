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
    # Serve OpenAPI + Swagger UI. Defaults to off in prod; set True to force on.
    api_docs_enabled: bool | None = None

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
                self.database_url = f"{prefix}{resolved.as_posix()}"
        return self

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:5173"

    # ML Models
    embedder_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    model_version: str = "kaushalpath-rank-0.1.0"

    # LLM Settings (Phase 12 conversational engine)
    llm_provider: str = "none"  # "none" | "openai_compat" | "gemini"
    llm_base_url: str | None = None
    llm_model: str = "gpt-4o-mini"
    llm_api_key: str | None = None

    # Resistance Score Settings (Phase 13 parental resistance tracking)
    resistance_w_topic: float = 0.40
    resistance_w_intensity: float = 0.40
    resistance_w_consensus: float = 0.20
    resistance_topic_weights: dict[str, float] = {
        "safety": 1.0,
        "social": 0.85,
        "distance": 0.75,
        "cost": 0.70,
        "security": 0.65,
        "income": 0.50,
        "other": 0.30,
    }

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

    @model_validator(mode="after")
    def _prod_hardening(self) -> Settings:
        """Fail fast if prod is misconfigured (Phase 9 security pass).

        These are the classic demo-to-prod foot-guns: shipping the dev secret
        key, a wildcard CORS origin with credentials, or an exposed debug/stack
        trace. Rather than silently running insecure, we refuse to boot.
        """
        if self.app_env.lower() == "prod":
            if self.secret_key == "dev-only-insecure-change-me":
                raise ValueError("SECRET_KEY must be overridden in prod (see .env.example).")
            if "*" in self.cors_origin_list:
                raise ValueError("CORS_ORIGINS must not contain '*' in prod.")
            if self.debug:
                raise ValueError("DEBUG must be false in prod.")
        return self

    @property
    def is_production(self) -> bool:
        return self.app_env.lower() == "prod"

    @property
    def docs_enabled(self) -> bool:
        """Swagger/OpenAPI: on outside prod unless explicitly overridden."""
        if self.api_docs_enabled is None:
            return not self.is_production
        return self.api_docs_enabled

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

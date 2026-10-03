"""Application configuration.

All settings are read from the environment / `.env` (pydantic-settings).
No hard-coded secrets — see `.env.example`. Defaults are dev-safe so the
test-suite and `make check` run without a populated `.env`.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # Database (SQLite for dev per docs/02_ARCHITECTURE.md)
    database_url: str = "sqlite:///./kaushalpath.db"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:5173"

    # ML Models
    embedder_model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    
    # Fallback ranker weights (if LightGBM model is not trained)
    ranker_weight_riasec: float = 0.4
    ranker_weight_aptitude: float = 0.2
    ranker_weight_fee: float = -0.1
    ranker_weight_retrieval: float = 0.3

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

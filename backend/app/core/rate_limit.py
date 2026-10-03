"""Shared slowapi rate limiter.

Defined here (not in `main`) so route modules can decorate their endpoints
without a circular import, while `main` registers it on `app.state`. Enabled per
settings; the test-suite forces it off in `conftest`.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

limiter = Limiter(key_func=get_remote_address, enabled=get_settings().rate_limit_enabled)

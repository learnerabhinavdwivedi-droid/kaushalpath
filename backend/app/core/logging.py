"""Structured logging with request-id propagation.

Every log line carries the active `request_id` (set by the middleware in
`app.main`) so a single request can be traced across services/logs.
"""
from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import LogRecord

request_id_var: ContextVar[str] = ContextVar("request_id", default="-")


class RequestIdFilter(logging.Filter):
    def filter(self, record: LogRecord) -> bool:
        record.request_id = request_id_var.get()
        return True


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    if root.handlers:  # idempotent — avoid duplicate handlers on reload
        return
    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(RequestIdFilter())
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] rid=%(request_id)s %(message)s"
    )
    handler.setFormatter(formatter)
    root.addHandler(handler)
    root.setLevel(getattr(logging, level.upper(), logging.INFO))


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

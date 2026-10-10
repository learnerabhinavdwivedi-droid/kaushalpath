"""Shared helpers for the Phase 1 data loaders.

Loader scripts live in `kaushalpath/scripts/` but import the app package from
`kaushalpath/backend/`. This module bootstraps the import path and provides an
idempotent upsert so every loader can be run repeatedly with stable row counts.
"""
from __future__ import annotations

import csv
import pathlib
import sys
from collections.abc import Iterable
from typing import Any

# --- path bootstrap -----------------------------------------------------------
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

DATA_DIR = BACKEND_DIR / "app" / "data"
SEED_DIR = DATA_DIR / "seed"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


def read_csv(path: pathlib.Path) -> list[dict[str, str]]:
    """Read a CSV file into a list of row dicts (empty file -> [])."""
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def to_bool(value: Any, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def to_int(value: Any) -> int | None:
    if value is None or str(value).strip() == "":
        return None
    return int(float(value))


def to_float(value: Any) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    return float(value)


def check_provenance(model: Any, key: dict[str, Any], values: dict[str, Any]) -> None:
    """Enforce Data Addendum Rule 1: No loader writes without provenance."""
    if hasattr(model, "evidence_grade") or hasattr(model, "source"):
        combined = {**key, **values}
        source = combined.get("source")
        if not source or not str(source).strip():
            raise ValueError(
                f"Missing required provenance field 'source' for model {model.__name__} "
                "(DATA ADDENDUM Rule 1)"
            )
        if hasattr(model, "evidence_grade"):
            grade = combined.get("evidence_grade")
            if not grade or grade not in {"A", "B", "C", "D"}:
                raise ValueError(
                    f"Missing or invalid required provenance field 'evidence_grade' "
                    f"for model {model.__name__}: got {grade!r} (DATA ADDENDUM Rule 1)"
                )
        if hasattr(model, "retrieved_on"):
            retrieved = combined.get("retrieved_on")
            if not retrieved or not str(retrieved).strip():
                raise ValueError(
                    f"Missing required provenance field 'retrieved_on' for model {model.__name__} "
                    "(DATA ADDENDUM Rule 1)"
                )


def upsert(
    session: Any,
    model: Any,
    key: dict[str, Any],
    values: dict[str, Any],
) -> str:
    """Insert-or-update a row by its natural key. Returns 'insert' or 'update'."""
    check_provenance(model, key, values)
    obj = session.query(model).filter_by(**key).one_or_none()
    if obj is None:
        obj = model(**key, **values)
        session.add(obj)
        return "insert"
    for field, value in values.items():
        setattr(obj, field, value)
    return "update"


def bulk_upsert(
    session: Any,
    model: Any,
    key_fields: Iterable[str],
    rows: Iterable[dict[str, Any]],
) -> tuple[int, int]:
    """Upsert many rows. `rows` each contain every `key_fields` entry.

    Returns (inserts, updates).
    """
    key_fields = list(key_fields)
    inserts = updates = 0
    for row in rows:
        key = {k: row[k] for k in key_fields}
        if any(v is None for v in key.values()):
            raise ValueError(f"natural key {key_fields} has a None value: {key}")
        values = {k: v for k, v in row.items() if k not in key_fields}
        if upsert(session, model, key, values) == "insert":
            inserts += 1
        else:
            updates += 1
    return inserts, updates

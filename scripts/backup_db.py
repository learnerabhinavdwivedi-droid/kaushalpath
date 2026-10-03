"""Phase 9 reliability: consistent SQLite backup.

Uses the sqlite3 online-backup API (not a raw file copy) so the snapshot is
transaction-consistent even while the app is serving. Postgres/other URLs are
out of scope for the dev/demo DB; the script refuses rather than silently
copying a partial file.

Usage:
    python scripts/backup_db.py            # -> backups/kaushalpath-<UTC ts>.db
    python scripts/backup_db.py --dest DIR
"""
from __future__ import annotations

import argparse
import pathlib
import sqlite3
from datetime import UTC, datetime

from _common import REPO_ROOT  # bootstraps sys.path to import the app package
from app.core.config import get_settings

_PREFIX = "sqlite:///"


def _sqlite_path(database_url: str) -> pathlib.Path:
    if not database_url.startswith(_PREFIX):
        raise SystemExit(
            f"backup_db supports SQLite only (got {database_url!r}). "
            "Use pg_dump for PostgreSQL."
        )
    raw = database_url[len(_PREFIX) :]
    if ":memory:" in raw:
        raise SystemExit("Cannot back up an in-memory database.")
    return pathlib.Path(raw).resolve()


def backup(dest_dir: pathlib.Path) -> pathlib.Path:
    src = _sqlite_path(get_settings().database_url)
    if not src.exists():
        raise SystemExit(f"Source database not found: {src}")
    dest_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    out = dest_dir / f"{src.stem}-{ts}.db"
    with sqlite3.connect(src) as source, sqlite3.connect(out) as target:
        source.backup(target)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Consistent SQLite backup")
    parser.add_argument(
        "--dest",
        default=str(REPO_ROOT / "backups"),
        help="Destination directory (default: <repo>/backups).",
    )
    args = parser.parse_args()
    out = backup(pathlib.Path(args.dest))
    print(f"Backed up {get_settings().database_url} -> {out}")


if __name__ == "__main__":
    main()

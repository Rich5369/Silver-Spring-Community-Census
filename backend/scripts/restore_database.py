"""Restore a shipped SQLite snapshot into the configured runtime database.

Usage:
    python scripts/restore_database.py path/to/community.seed.db

The destination is resolved from DATABASE_URL in the same way as the API.
This is intentionally a copy operation: ingestion remains the source of truth
when a fresh dataset is required.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from app.core.config import BACKEND_DIR, get_settings


def database_path() -> Path:
    url = get_settings().database_url
    prefix = "sqlite:///"
    if not url.startswith(prefix):
        raise SystemExit("restore_database.py only supports sqlite DATABASE_URL values")
    path = Path(url[len(prefix) :])
    return path if path.is_absolute() else BACKEND_DIR / path


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: python scripts/restore_database.py SNAPSHOT.db")
    source = Path(sys.argv[1]).resolve()
    if not source.is_file():
        raise SystemExit(f"snapshot not found: {source}")

    destination = database_path()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".restore.tmp")
    shutil.copy2(source, temporary)
    temporary.replace(destination)
    print(f"Restored {source} -> {destination}")


if __name__ == "__main__":
    main()

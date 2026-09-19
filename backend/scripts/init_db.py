"""Create the database schema.

Run from the ``backend/`` directory::

    python -m scripts.init_db

Idempotent: existing tables are left alone. Creates no data - seeding real
content is the job of ingestion, and the only seeded rows anywhere in this
project are the clearly labelled TEST fixtures used by the test suite.
"""

from __future__ import annotations

from app.core.config import get_settings
from app.core.database import engine, init_database
from app.models import Base


def main() -> None:
    """Create all tables and report what now exists."""
    settings = get_settings()
    print(f"Database: {settings.database_url}")

    init_database()

    tables = sorted(Base.metadata.tables)
    print(f"Schema ready. {len(tables)} table(s):")
    for table in tables:
        print(f"  - {table}")

    engine.dispose()


if __name__ == "__main__":
    main()

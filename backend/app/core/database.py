"""SQLAlchemy engine and session management.

SQLite is the storage engine for the hackathon MVP: it needs no server, the
whole database is one file that can be deleted and rebuilt by re-running
ingestion, and it is more than fast enough for a single neighbourhood's worth
of public data. The ``DATABASE_URL`` indirection means moving to Postgres later
is a configuration change rather than a rewrite.
"""

from __future__ import annotations

from collections.abc import Generator
from pathlib import Path

import sqlite3

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.engine import make_url

from app.core.config import BACKEND_DIR, Settings, get_settings


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection: object, _connection_record: object) -> None:
    """Turn on foreign key enforcement for every SQLite connection.

    SQLite ships with foreign keys **disabled** and applies the pragma per
    connection, so without this every ``ForeignKey`` in the models would be
    inert documentation: orphaned rows would insert happily and the evidence
    guarantee would be unenforced. Registered against the generic ``Engine``
    and gated on the driver so a future Postgres URL is unaffected.
    """
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def _prepare_sqlite_path(database_url: str) -> None:
    """Create the parent directory for a file-backed SQLite database.

    SQLAlchemy will not create missing directories, so a default of
    ``sqlite:///./data/community.db`` fails on a fresh checkout unless the
    ``data/`` directory exists. Relative paths are resolved against the
    ``backend/`` directory so the database lands in the same place regardless
    of the working directory the server was started from.
    """
    prefix = "sqlite:///"
    if not database_url.startswith(prefix):
        return

    raw_path = database_url[len(prefix) :]
    # ":memory:" and the empty (temp-file) form have no directory to create.
    if not raw_path or raw_path.startswith(":"):
        return

    path = Path(raw_path)
    if not path.is_absolute():
        path = BACKEND_DIR / path
    path.parent.mkdir(parents=True, exist_ok=True)


def create_database_engine(settings: Settings | None = None) -> Engine:
    """Build a SQLAlchemy :class:`~sqlalchemy.Engine` from settings."""
    settings = settings or get_settings()
    database_url = make_url(settings.database_url)
    if database_url.get_backend_name() == 'sqlite' and database_url.database not in (None, '', ':memory:'):
        path = Path(database_url.database)
        if not path.is_absolute():
            database_url = database_url.set(database=str(BACKEND_DIR / path))
    _prepare_sqlite_path(str(database_url))

    connect_args: dict[str, object] = {}
    if settings.is_sqlite:
        # FastAPI serves requests from a thread pool, so the connection may be
        # used from a different thread than the one that created it.
        connect_args["check_same_thread"] = False

    return create_engine(
        database_url,
        echo=settings.database_echo,
        connect_args=connect_args,
        future=True,
    )


engine: Engine = create_database_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session per request.

    The session is always closed, and rolled back if the request handler
    raised, so a failed request never leaves a transaction open.
    """
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_database() -> None:
    """Create any tables declared on :class:`app.models.base.Base`.

    Safe to call repeatedly: ``create_all`` skips tables that already exist.
    """
    # Imported here rather than at module scope to avoid a circular import
    # (models import nothing from this module, but repositories do). The
    # package __init__ registers every model on Base.metadata.
    from app.models import Base

    Base.metadata.create_all(bind=engine)

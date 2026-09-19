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

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import BACKEND_DIR, Settings, get_settings


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
    _prepare_sqlite_path(settings.database_url)

    connect_args: dict[str, object] = {}
    if settings.is_sqlite:
        # FastAPI serves requests from a thread pool, so the connection may be
        # used from a different thread than the one that created it.
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
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

    A no-op today because no domain models exist yet. It is wired up now so
    that adding the first table (provenance-carrying Census observations and
    OpenStreetMap places) requires no changes to application startup.
    """
    # Imported here rather than at module scope so that importing the engine
    # never pulls in the whole model package.
    from app.models.base import Base

    Base.metadata.create_all(bind=engine)

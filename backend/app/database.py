"""SQLAlchemy database setup."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


# SQLite needs check_same_thread=False for FastAPI's threading model
connect_args = {}
if settings.database_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    pool_pre_ping=True,
)

# Enable WAL mode for SQLite (better concurrent read performance)
if settings.database_url.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables."""
    from app import models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _ensure_lightweight_columns()


def _ensure_lightweight_columns() -> None:
    """Add columns introduced after the MVP tables were first created.

    This keeps the local SQLite-first workflow painless without bringing in
    Alembic for every small portfolio iteration. Production deployments should
    still use explicit migrations.
    """
    inspector = inspect(engine)
    if "meetings" not in inspector.get_table_names():
        return
    columns = {col["name"] for col in inspector.get_columns("meetings")}
    additions = []
    if "processing_stage" not in columns:
        additions.append("ADD COLUMN processing_stage VARCHAR(100)")
    if "progress_percent" not in columns:
        additions.append("ADD COLUMN progress_percent INTEGER DEFAULT 0")

    if not additions:
        return

    with engine.begin() as conn:
        for addition in additions:
            conn.execute(text(f"ALTER TABLE meetings {addition}"))

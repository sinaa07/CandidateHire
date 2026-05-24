"""SQLite database engine and session setup (metadata only)."""
from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for ORM tables."""


STORAGE_ROOT = Path("storage")
DB_PATH = STORAGE_ROOT / "candidatehire.db"
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

@event.listens_for(engine, "connect")
def _sqlite_enable_foreign_keys(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def init_db() -> None:
    """Create storage directory and all ORM tables."""
    STORAGE_ROOT.mkdir(parents=True, exist_ok=True)
    # Import tables so they register on Base.metadata
    from app.models import tables as _tables  # noqa: F401

    Base.metadata.create_all(bind=engine)

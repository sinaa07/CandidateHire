"""SQLAlchemy session factory and FastAPI dependency injection."""
from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.models.db import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session and always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

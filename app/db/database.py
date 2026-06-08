"""Database engine, session factory and FastAPI dependency."""
from __future__ import annotations

import os
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _make_engine(database_url: str):
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Needed for SQLite when used across threads (uvicorn workers).
        connect_args["check_same_thread"] = False
        # Ensure the parent directory exists for file-based SQLite.
        if ":///" in database_url:
            path = database_url.split(":///", 1)[1]
            if path and path != ":memory:":
                parent = os.path.dirname(path)
                if parent:
                    os.makedirs(parent, exist_ok=True)
    return create_engine(database_url, connect_args=connect_args, future=True)


_settings = get_settings()
engine = _make_engine(_settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables. Import models so they register on Base.metadata."""
    from app import models  # noqa: F401  (registers mappers)

    Base.metadata.create_all(bind=engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

"""Data access for memories (long-term facts)."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Memory


class MemoryRepository:
    def __init__(self, db: DBSession) -> None:
        self.db = db

    def upsert(self, session_id: str, category: str, value: str) -> Memory | None:
        """Insert a fact, ignoring duplicates (unique session/category/value).

        Returns the new Memory, or None if it already existed.
        """
        existing = self.db.scalar(
            select(Memory).where(
                Memory.session_id == session_id,
                Memory.category == category,
                Memory.value == value,
            )
        )
        if existing is not None:
            return None
        mem = Memory(session_id=session_id, category=category, value=value)
        self.db.add(mem)
        self.db.commit()
        self.db.refresh(mem)
        return mem

    def list_for_session(self, session_id: str) -> list[Memory]:
        return list(
            self.db.scalars(
                select(Memory)
                .where(Memory.session_id == session_id)
                .order_by(Memory.created_at.asc())
            )
        )

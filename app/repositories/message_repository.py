"""Data access for messages."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Message


class MessageRepository:
    def __init__(self, db: DBSession) -> None:
        self.db = db

    def create(
        self, session_id: str, role: str, content: str, token_count: int
    ) -> Message:
        msg = Message(
            session_id=session_id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def get(self, message_id: int) -> Message | None:
        return self.db.get(Message, message_id)

    def list_for_session(
        self, session_id: str, include_archived: bool = True
    ) -> list[Message]:
        stmt = select(Message).where(Message.session_id == session_id)
        if not include_archived:
            stmt = stmt.where(Message.archived.is_(False))
        return list(self.db.scalars(stmt.order_by(Message.created_at.asc())))

    def recent_active(self, session_id: str, limit: int) -> list[Message]:
        """Most recent non-archived messages, returned oldest-first."""
        stmt = (
            select(Message)
            .where(Message.session_id == session_id, Message.archived.is_(False))
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        rows = list(self.db.scalars(stmt))
        return list(reversed(rows))

    def archivable(self, session_id: str, keep_recent: int) -> list[Message]:
        """Active messages older than the ``keep_recent`` newest ones."""
        active = self.list_for_session(session_id, include_archived=False)
        if len(active) <= keep_recent:
            return []
        return active[: len(active) - keep_recent]

    def archive(self, messages: list[Message]) -> None:
        for m in messages:
            m.archived = True
        self.db.commit()

    def ids_for_session(self, session_id: str) -> list[int]:
        return list(
            self.db.scalars(
                select(Message.id).where(Message.session_id == session_id)
            )
        )

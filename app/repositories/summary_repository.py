"""Data access for summaries."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Summary


class SummaryRepository:
    def __init__(self, db: DBSession) -> None:
        self.db = db

    def create(
        self,
        session_id: str,
        content: str,
        covers_from_id: int | None,
        covers_to_id: int | None,
        message_count: int,
        token_count: int,
    ) -> Summary:
        summary = Summary(
            session_id=session_id,
            content=content,
            covers_from_id=covers_from_id,
            covers_to_id=covers_to_id,
            message_count=message_count,
            token_count=token_count,
        )
        self.db.add(summary)
        self.db.commit()
        self.db.refresh(summary)
        return summary

    def list_for_session(self, session_id: str) -> list[Summary]:
        return list(
            self.db.scalars(
                select(Summary)
                .where(Summary.session_id == session_id)
                .order_by(Summary.created_at.asc())
            )
        )

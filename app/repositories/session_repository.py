"""Data access for sessions."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from app.models import Session


class SessionRepository:
    def __init__(self, db: DBSession) -> None:
        self.db = db

    def create(self, title: str | None = None) -> Session:
        session = Session(title=title)
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def get(self, session_id: str) -> Session | None:
        return self.db.get(Session, session_id)

    def list(self) -> list[Session]:
        return list(
            self.db.scalars(select(Session).order_by(Session.created_at.desc()))
        )

    def delete(self, session: Session) -> None:
        self.db.delete(session)
        self.db.commit()

    def add_tokens(self, session: Session, tokens: int) -> None:
        session.token_count = (session.token_count or 0) + tokens
        self.db.commit()

    def set_tokens(self, session: Session, tokens: int) -> None:
        session.token_count = tokens
        self.db.commit()

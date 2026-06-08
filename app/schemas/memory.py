"""Memory & summary API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MemoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    category: str
    value: str
    created_at: datetime


class SummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    content: str
    covers_from_id: int | None
    covers_to_id: int | None
    message_count: int
    token_count: int
    created_at: datetime

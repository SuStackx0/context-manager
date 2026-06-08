"""Message API schemas."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import Role


class MessageCreate(BaseModel):
    session_id: str
    role: Role
    content: str = Field(min_length=1)


class MessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    session_id: str
    role: str
    content: str
    token_count: int
    archived: bool
    created_at: datetime

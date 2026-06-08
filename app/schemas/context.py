"""Context build API schemas."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ContextBuildRequest(BaseModel):
    session_id: str
    query: str = Field(min_length=1)


class ContextItem(BaseModel):
    source: str  # "memory" | "summary" | "recent" | "retrieved"
    content: str
    token_count: int
    ref_id: int | str | None = None


class SectionStat(BaseModel):
    section: str
    included: int
    dropped: int
    tokens_used: int


class ContextPackage(BaseModel):
    session_id: str
    query: str | None = None
    prompt: str  # the assembled, ready-to-send context string
    items: list[ContextItem]
    total_tokens: int
    max_tokens: int
    sections: list[SectionStat]


class DebugDroppedItem(BaseModel):
    source: str
    ref_id: int | str | None
    token_count: int
    reason: str


class ContextDebug(BaseModel):
    session_id: str
    query: str | None
    max_tokens: int
    total_tokens: int
    sections: list[SectionStat]
    included: list[ContextItem]
    dropped: list[DebugDroppedItem]
    compression_triggered: bool

"""Memory endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Services, get_services
from app.schemas.memory import MemoryRead

router = APIRouter(tags=["memories"])


@router.get("/memories/{session_id}", response_model=list[MemoryRead])
def get_memories(
    session_id: str, svc: Services = Depends(get_services)
) -> list[MemoryRead]:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        MemoryRead.model_validate(m)
        for m in svc.memories.list_for_session(session_id)
    ]

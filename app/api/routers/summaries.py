"""Summary endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Services, get_services
from app.schemas.memory import SummaryRead

router = APIRouter(tags=["summaries"])


@router.get("/summaries/{session_id}", response_model=list[SummaryRead])
def get_summaries(
    session_id: str, svc: Services = Depends(get_services)
) -> list[SummaryRead]:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        SummaryRead.model_validate(s)
        for s in svc.summaries.list_for_session(session_id)
    ]


@router.post("/summaries/{session_id}/compress")
def compress_session(
    session_id: str, svc: Services = Depends(get_services)
) -> dict:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return svc.summary.compress(session_id)

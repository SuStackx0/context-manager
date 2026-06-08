"""Context build endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import Services, get_services
from app.schemas.context import ContextBuildRequest, ContextDebug, ContextPackage

router = APIRouter(prefix="/context", tags=["context"])


@router.post("/build", response_model=ContextPackage)
def build_context(
    payload: ContextBuildRequest, svc: Services = Depends(get_services)
) -> ContextPackage:
    if svc.sessions.get(payload.session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return svc.context.build(payload.session_id, payload.query)


@router.get("/{session_id}", response_model=ContextPackage)
def get_context(
    session_id: str, svc: Services = Depends(get_services)
) -> ContextPackage:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return svc.context.get_default(session_id)


@router.get("/{session_id}/debug", response_model=ContextDebug)
def debug_context(
    session_id: str,
    query: str | None = None,
    svc: Services = Depends(get_services),
) -> ContextDebug:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return svc.context.debug(session_id, query)

"""Session endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import Services, get_services
from app.schemas.session import SessionCreate, SessionRead

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionRead, status_code=status.HTTP_201_CREATED)
def create_session(
    payload: SessionCreate, svc: Services = Depends(get_services)
) -> SessionRead:
    session = svc.sessions.create(title=payload.title)
    return SessionRead.model_validate(session)


@router.get("", response_model=list[SessionRead])
def list_sessions(svc: Services = Depends(get_services)) -> list[SessionRead]:
    return [SessionRead.model_validate(s) for s in svc.sessions.list()]


@router.get("/{session_id}", response_model=SessionRead)
def get_session(
    session_id: str, svc: Services = Depends(get_services)
) -> SessionRead:
    session = svc.sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return SessionRead.model_validate(session)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, svc: Services = Depends(get_services)) -> None:
    session = svc.sessions.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    # Remove FAISS vectors before the rows disappear, keeping the index in sync.
    svc.retrieval.remove_session(session_id)
    svc.sessions.delete(session)

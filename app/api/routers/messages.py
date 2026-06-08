"""Message endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import Services, get_services
from app.schemas.message import MessageCreate, MessageRead

router = APIRouter(tags=["messages"])


@router.post("/messages", response_model=MessageRead, status_code=status.HTTP_201_CREATED)
def add_message(
    payload: MessageCreate, svc: Services = Depends(get_services)
) -> MessageRead:
    session = svc.sessions.get(payload.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    token_count = svc.tokens.count(payload.content)
    msg = svc.messages.create(
        session_id=payload.session_id,
        role=payload.role.value,
        content=payload.content,
        token_count=token_count,
    )
    # Embed + index immediately (cheap); never blocks on the LLM.
    svc.retrieval.index_message(msg.id, payload.content)
    svc.sessions.add_tokens(session, token_count)
    return MessageRead.model_validate(msg)


@router.get("/messages/{session_id}", response_model=list[MessageRead])
def get_messages(
    session_id: str, svc: Services = Depends(get_services)
) -> list[MessageRead]:
    if svc.sessions.get(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    msgs = svc.messages.list_for_session(session_id, include_archived=True)
    return [MessageRead.model_validate(m) for m in msgs]

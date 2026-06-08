"""Health endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session as DBSession

from app.api.deps import Singletons, get_singletons
from app.db.database import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(
    db: DBSession = Depends(get_db), sg: Singletons = Depends(get_singletons)
) -> dict:
    db_ok = True
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_ok = False
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "vector_store_size": sg.vector_store.size,
        "llm_provider": sg.settings.llm_provider,
        "embedding_provider": sg.settings.embedding_provider,
    }

"""Dependency wiring.

Heavyweight, stateful singletons (providers, FAISS index, token service) are
built once at startup and held on ``app.state``. Per-request services are
assembled cheaply from those singletons plus the request-scoped DB session.
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session as DBSession

from app.core.config import Settings, get_settings
from app.db.database import get_db
from app.db.vector_store import FaissVectorStore
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.factory import build_embedding_provider, build_llm_provider
from app.repositories.memory_repository import MemoryRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.summary_repository import SummaryRepository
from app.services.context_service import ContextService
from app.services.embedding_service import EmbeddingService
from app.services.memory_service import MemoryService
from app.services.retrieval_service import RetrievalService
from app.services.summary_service import SummaryService
from app.services.token_service import TokenService


@dataclass
class Singletons:
    """Process-wide, expensive-to-build objects."""

    settings: Settings
    embedding_provider: EmbeddingProvider
    llm_provider: LLMProvider
    vector_store: FaissVectorStore
    token_service: TokenService


def build_singletons(settings: Settings) -> Singletons:
    embedding_provider = build_embedding_provider(settings)
    llm_provider = build_llm_provider(settings)
    vector_store = FaissVectorStore(
        dim=settings.embedding_dim, index_path=settings.faiss_index_path
    )
    token_model = (
        settings.llm_model_name if settings.llm_provider == "local" else None
    )
    token_service = TokenService(model_name=token_model)
    return Singletons(
        settings=settings,
        embedding_provider=embedding_provider,
        llm_provider=llm_provider,
        vector_store=vector_store,
        token_service=token_service,
    )


def get_singletons(request: Request) -> Singletons:
    return request.app.state.singletons


@dataclass
class Services:
    """Per-request service bundle."""

    settings: Settings
    sessions: SessionRepository
    messages: MessageRepository
    memories: MemoryRepository
    summaries: SummaryRepository
    tokens: TokenService
    embeddings: EmbeddingService
    retrieval: RetrievalService
    memory: MemoryService
    summary: SummaryService
    context: ContextService


def get_services(
    db: DBSession = Depends(get_db),
    sg: Singletons = Depends(get_singletons),
) -> Services:
    s = sg.settings
    sessions = SessionRepository(db)
    messages = MessageRepository(db)
    memories = MemoryRepository(db)
    summaries = SummaryRepository(db)

    embeddings = EmbeddingService(sg.embedding_provider)
    retrieval = RetrievalService(
        store=sg.vector_store,
        embeddings=embeddings,
        messages=messages,
        top_k=s.retrieval_top_k,
        overfetch=s.retrieval_overfetch,
    )
    memory = MemoryService(memories, sg.llm_provider)
    summary = SummaryService(
        sessions=sessions,
        messages=messages,
        summaries=summaries,
        memory_service=memory,
        tokens=sg.token_service,
        llm=sg.llm_provider,
        keep_recent=s.recent_messages_keep,
        max_new_tokens=s.llm_max_new_tokens,
    )
    context = ContextService(
        sessions=sessions,
        messages=messages,
        memories=memories,
        summaries=summaries,
        retrieval=retrieval,
        summary_service=summary,
        tokens=sg.token_service,
        max_context_tokens=s.max_context_tokens,
        compress_threshold=s.compress_token_threshold,
        recent_keep=s.recent_messages_keep,
        top_k=s.retrieval_top_k,
    )
    return Services(
        settings=s,
        sessions=sessions,
        messages=messages,
        memories=memories,
        summaries=summaries,
        tokens=sg.token_service,
        embeddings=embeddings,
        retrieval=retrieval,
        memory=memory,
        summary=summary,
        context=context,
    )

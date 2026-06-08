"""Semantic retrieval over message embeddings.

Vectors live in a single FAISS index keyed by message_id. Per-session filtering
is done by over-fetching globally then filtering to the session's message ids
(correct and simple at this scale). Archived messages remain searchable so
compressed history is still reachable.
"""
from __future__ import annotations

from app.db.vector_store import FaissVectorStore
from app.repositories.message_repository import MessageRepository
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    def __init__(
        self,
        store: FaissVectorStore,
        embeddings: EmbeddingService,
        messages: MessageRepository,
        top_k: int = 5,
        overfetch: int = 5,
    ) -> None:
        self.store = store
        self.embeddings = embeddings
        self.messages = messages
        self.top_k = top_k
        self.overfetch = overfetch

    def index_message(self, message_id: int, content: str) -> None:
        vec = self.embeddings.embed_one(content)
        self.store.add([message_id], [vec])

    def search(
        self, session_id: str, query: str, k: int | None = None
    ) -> list[tuple[int, float]]:
        """Return [(message_id, score)] for the session, most-relevant first."""
        k = k or self.top_k
        session_ids = set(self.messages.ids_for_session(session_id))
        if not session_ids:
            return []
        query_vec = self.embeddings.embed_one(query)
        # Over-fetch globally, then keep only this session's messages.
        candidates = self.store.search(query_vec, k * self.overfetch)
        filtered = [(mid, score) for mid, score in candidates if mid in session_ids]
        return filtered[:k]

    def remove_session(self, session_id: str) -> int:
        ids = self.messages.ids_for_session(session_id)
        return self.store.remove_ids(ids)

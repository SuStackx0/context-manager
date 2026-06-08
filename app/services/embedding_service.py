"""Embedding service — thin wrapper over the configured EmbeddingProvider."""
from __future__ import annotations

from app.providers.base import EmbeddingProvider


class EmbeddingService:
    def __init__(self, provider: EmbeddingProvider) -> None:
        self.provider = provider

    def embed_one(self, text: str) -> list[float]:
        return self.provider.embed_one(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        return self.provider.embed(texts)

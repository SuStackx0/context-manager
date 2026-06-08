"""Provider factory — selects implementation from settings."""
from __future__ import annotations

from app.core.config import Settings
from app.providers.base import EmbeddingProvider, LLMProvider
from app.providers.fake import FakeEmbeddingProvider, FakeLLMProvider


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "fake":
        return FakeEmbeddingProvider(dim=settings.embedding_dim)
    from app.providers.local import LocalEmbeddingProvider

    return LocalEmbeddingProvider(
        model_name=settings.embedding_model_name, dim=settings.embedding_dim
    )


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "fake":
        return FakeLLMProvider()
    from app.providers.local import LocalLLMProvider

    return LocalLLMProvider(model_name=settings.llm_model_name)

"""Provider interfaces for LLM and embedding backends.

These abstractions keep the service layer independent of any specific model
stack, satisfying the extensibility requirement (multiple LLM / embedding
providers) and enabling deterministic fakes for tests.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Turns text into fixed-dimension vectors."""

    dim: int

    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding per input text."""

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class LLMProvider(ABC):
    """Generates text — used for summarization and memory extraction."""

    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int = 256) -> str:
        """Return the model's completion for ``prompt``."""

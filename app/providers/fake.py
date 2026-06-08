"""Deterministic fake providers for tests and offline smoke runs.

No torch / transformers required. Embeddings are a stable hashing-based vector;
the LLM produces a simple extractive summary and rule-based memory JSON so that
the full pipeline can be exercised without loading a model.
"""
from __future__ import annotations

import hashlib
import json
import re

from app.providers.base import EmbeddingProvider, LLMProvider

_PROFESSION_RE = re.compile(
    r"\b(?:i\s+(?:work\s+as|am)\s+(?:an?\s+)?)([A-Z][A-Za-z ]+?)(?:\.|,|\band\b|$)",
    re.IGNORECASE,
)
_TECH_RE = re.compile(
    r"\b(python|fastapi|django|flask|java|javascript|typescript|react|"
    r"postgres(?:ql)?|mysql|sqlite|redis|docker|kubernetes|pytorch|"
    r"tensorflow|go|rust|c\+\+|node\.?js|sql|aws|gcp|azure)\b",
    re.IGNORECASE,
)
_GOAL_RE = re.compile(
    r"\b(?:i\s+want\s+to|my\s+goal\s+is\s+to|i'?m\s+trying\s+to)\s+([^.,\n]+)",
    re.IGNORECASE,
)


class FakeEmbeddingProvider(EmbeddingProvider):
    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vec(t) for t in texts]

    def _vec(self, text: str) -> list[float]:
        # Deterministic pseudo-embedding from a hash of the text.
        h = hashlib.sha256(text.lower().encode("utf-8")).digest()
        # Expand the 32-byte digest to ``dim`` floats in [-1, 1].
        vals = []
        i = 0
        while len(vals) < self.dim:
            b = h[i % len(h)]
            vals.append((b / 127.5) - 1.0)
            i += 1
        return vals


class FakeLLMProvider(LLMProvider):
    """Extractive summary + rule-based memory extraction (no model)."""

    def generate(self, prompt: str, max_new_tokens: int = 256) -> str:
        if "Extract facts" in prompt or "JSON" in prompt:
            return self._extract_memories_json(prompt)
        return self._summarize(prompt)

    def _summarize(self, prompt: str) -> str:
        # Grab the conversation body after a marker if present.
        body = prompt
        if "Conversation:" in prompt:
            body = prompt.split("Conversation:", 1)[1]
        sentences = re.split(r"(?<=[.!?])\s+", body.strip())
        keep = [s for s in sentences if s.strip()][:3]
        return "Summary: " + " ".join(keep) if keep else "Summary: (empty)"

    def _extract_memories_json(self, prompt: str) -> str:
        facts = []
        for m in _PROFESSION_RE.finditer(prompt):
            facts.append({"category": "profession", "value": m.group(1).strip()})
        for m in _TECH_RE.finditer(prompt):
            facts.append({"category": "technology", "value": m.group(1).strip()})
        for m in _GOAL_RE.finditer(prompt):
            facts.append({"category": "goal", "value": m.group(1).strip()})
        return json.dumps(facts)

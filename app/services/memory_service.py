"""Memory extraction service.

Uses the LLM to extract long-term facts as JSON, parses tolerantly (a parse
failure drops the fact and never raises), and persists with dedup via the
repository's unique constraint.
"""
from __future__ import annotations

import json
import re

from app.core.constants import MemoryCategory
from app.core.logging import get_logger
from app.providers.base import LLMProvider
from app.repositories.memory_repository import MemoryRepository

logger = get_logger(__name__)

_VALID = {c.value for c in MemoryCategory}

_PROMPT = """Extract facts about the user as a JSON array of objects with keys \
"category" and "value". Allowed categories: profession, technology, preference, \
goal, topic. Only include facts explicitly stated. Respond with JSON only.

Conversation:
{text}

JSON:"""


class MemoryService:
    def __init__(self, repo: MemoryRepository, llm: LLMProvider) -> None:
        self.repo = repo
        self.llm = llm

    def extract_and_store(self, session_id: str, text: str) -> list:
        raw = self.llm.generate(_PROMPT.format(text=text), max_new_tokens=256)
        facts = self._parse(raw)
        stored = []
        for category, value in facts:
            mem = self.repo.upsert(session_id, category, value)
            if mem is not None:
                stored.append(mem)
        return stored

    def _parse(self, raw: str) -> list[tuple[str, str]]:
        """Best-effort JSON extraction. Never raises."""
        data = self._loads_lenient(raw)
        if not isinstance(data, list):
            return []
        out: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in data:
            if not isinstance(item, dict):
                continue
            category = str(item.get("category", "")).strip().lower()
            value = str(item.get("value", "")).strip()
            if category not in _VALID or not value:
                continue
            key = (category, value.lower())
            if key in seen:
                continue
            seen.add(key)
            out.append((category, value))
        return out

    @staticmethod
    def _loads_lenient(raw: str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            pass
        # Try to salvage the first JSON array substring.
        match = re.search(r"\[.*\]", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                logger.debug("Could not parse salvaged memory JSON")
        return None

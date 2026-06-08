"""Summarization / compression service.

When a session exceeds the token threshold, old active messages are summarized
into a Summary row, memories are extracted from that span, and the messages are
*soft-archived* (archived=True) — never deleted, so their FAISS vectors remain
searchable via semantic retrieval.
"""
from __future__ import annotations

from app.core.logging import get_logger
from app.providers.base import LLMProvider
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.summary_repository import SummaryRepository
from app.services.memory_service import MemoryService
from app.services.token_service import TokenService

logger = get_logger(__name__)

_SUMMARY_PROMPT = """Summarize the following conversation segment concisely, \
preserving key facts, decisions, and context. 3-5 sentences.

Conversation:
{text}

Summary:"""


class SummaryService:
    def __init__(
        self,
        sessions: SessionRepository,
        messages: MessageRepository,
        summaries: SummaryRepository,
        memory_service: MemoryService,
        tokens: TokenService,
        llm: LLMProvider,
        keep_recent: int,
        max_new_tokens: int = 256,
    ) -> None:
        self.sessions = sessions
        self.messages = messages
        self.summaries = summaries
        self.memory_service = memory_service
        self.tokens = tokens
        self.llm = llm
        self.keep_recent = keep_recent
        self.max_new_tokens = max_new_tokens

    def compress(self, session_id: str) -> dict:
        session = self.sessions.get(session_id)
        if session is None:
            return {"compressed": False, "reason": "session not found"}

        to_archive = self.messages.archivable(session_id, self.keep_recent)
        if not to_archive:
            return {"compressed": False, "reason": "nothing to compress"}

        text = "\n".join(f"{m.role}: {m.content}" for m in to_archive)
        summary_text = self.llm.generate(
            _SUMMARY_PROMPT.format(text=text), max_new_tokens=self.max_new_tokens
        ).strip()
        summary_tokens = self.tokens.count(summary_text)

        summary = self.summaries.create(
            session_id=session_id,
            content=summary_text,
            covers_from_id=to_archive[0].id,
            covers_to_id=to_archive[-1].id,
            message_count=len(to_archive),
            token_count=summary_tokens,
        )

        # Extract long-term memories from the archived span (off the hot path).
        memories = self.memory_service.extract_and_store(session_id, text)

        # Soft-archive: keep rows + FAISS vectors; just flip the flag.
        self.messages.archive(to_archive)

        # Recompute session token_count from what now counts as "live" context:
        # active messages + summaries.
        self._recompute_tokens(session_id)

        logger.info(
            "Compressed session %s: archived %d msgs, +%d memories",
            session_id,
            len(to_archive),
            len(memories),
        )
        return {
            "compressed": True,
            "archived_messages": len(to_archive),
            "summary_id": summary.id,
            "new_memories": len(memories),
        }

    def _recompute_tokens(self, session_id: str) -> None:
        session = self.sessions.get(session_id)
        if session is None:
            return
        active = self.messages.recent_active(session_id, limit=10_000)
        summaries = self.summaries.list_for_session(session_id)
        total = sum(m.token_count for m in active) + sum(
            s.token_count for s in summaries
        )
        self.sessions.set_tokens(session, total)

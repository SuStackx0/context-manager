"""Context builder + token-budget optimizer.

Assembles an optimized context payload from memories, summaries, recent
messages and semantically-retrieved messages, allocating a fixed token budget
by section priority and recording what was dropped (for the debug endpoint).
"""
from __future__ import annotations

from app.repositories.memory_repository import MemoryRepository
from app.repositories.message_repository import MessageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.summary_repository import SummaryRepository
from app.schemas.context import (
    ContextDebug,
    ContextItem,
    ContextPackage,
    DebugDroppedItem,
    SectionStat,
)
from app.services.retrieval_service import RetrievalService
from app.services.summary_service import SummaryService
from app.services.token_service import TokenService

# Priority order: filled first, dropped last.
_SECTION_ORDER = ["memories", "summaries", "recent", "retrieved"]


class _Candidate:
    __slots__ = ("source", "content", "tokens", "ref_id")

    def __init__(self, source: str, content: str, tokens: int, ref_id):
        self.source = source
        self.content = content
        self.tokens = tokens
        self.ref_id = ref_id


class ContextService:
    def __init__(
        self,
        sessions: SessionRepository,
        messages: MessageRepository,
        memories: MemoryRepository,
        summaries: SummaryRepository,
        retrieval: RetrievalService,
        summary_service: SummaryService,
        tokens: TokenService,
        max_context_tokens: int,
        compress_threshold: int,
        recent_keep: int,
        top_k: int,
    ) -> None:
        self.sessions = sessions
        self.messages = messages
        self.memories = memories
        self.summaries = summaries
        self.retrieval = retrieval
        self.summary_service = summary_service
        self.tokens = tokens
        self.max_context_tokens = max_context_tokens
        self.compress_threshold = compress_threshold
        self.recent_keep = recent_keep
        self.top_k = top_k

    # ---- public API ----------------------------------------------------

    def build(self, session_id: str, query: str) -> ContextPackage:
        debug = self._assemble(session_id, query, run_compression=True)
        return self._to_package(session_id, query, debug)

    def get_default(self, session_id: str) -> ContextPackage:
        # No query => no semantic retrieval step.
        debug = self._assemble(session_id, query=None, run_compression=False)
        return self._to_package(session_id, None, debug)

    def debug(self, session_id: str, query: str | None) -> ContextDebug:
        return self._assemble(
            session_id, query, run_compression=bool(query)
        )

    # ---- internals -----------------------------------------------------

    def _assemble(
        self, session_id: str, query: str | None, run_compression: bool
    ) -> ContextDebug:
        compression_triggered = False
        session = self.sessions.get(session_id)
        if session is not None and run_compression:
            if (session.token_count or 0) > self.compress_threshold:
                result = self.summary_service.compress(session_id)
                compression_triggered = bool(result.get("compressed"))

        sections = self._gather_candidates(session_id, query)

        budget = self.max_context_tokens
        if query:
            budget = max(0, budget - self.tokens.count(query))

        included: list[ContextItem] = []
        dropped: list[DebugDroppedItem] = []
        stats: list[SectionStat] = []
        used_total = 0

        for name in _SECTION_ORDER:
            candidates = sections.get(name, [])
            inc_count = 0
            drop_count = 0
            section_tokens = 0
            for cand in candidates:
                if cand.tokens <= budget:
                    budget -= cand.tokens
                    used_total += cand.tokens
                    section_tokens += cand.tokens
                    inc_count += 1
                    included.append(
                        ContextItem(
                            source=cand.source,
                            content=cand.content,
                            token_count=cand.tokens,
                            ref_id=cand.ref_id,
                        )
                    )
                else:
                    drop_count += 1
                    dropped.append(
                        DebugDroppedItem(
                            source=cand.source,
                            ref_id=cand.ref_id,
                            token_count=cand.tokens,
                            reason="exceeds remaining token budget",
                        )
                    )
            stats.append(
                SectionStat(
                    section=name,
                    included=inc_count,
                    dropped=drop_count,
                    tokens_used=section_tokens,
                )
            )

        return ContextDebug(
            session_id=session_id,
            query=query,
            max_tokens=self.max_context_tokens,
            total_tokens=used_total,
            sections=stats,
            included=included,
            dropped=dropped,
            compression_triggered=compression_triggered,
        )

    def _gather_candidates(
        self, session_id: str, query: str | None
    ) -> dict[str, list[_Candidate]]:
        out: dict[str, list[_Candidate]] = {k: [] for k in _SECTION_ORDER}

        for mem in self.memories.list_for_session(session_id):
            content = f"[{mem.category}] {mem.value}"
            out["memories"].append(
                _Candidate("memory", content, self.tokens.count(content), mem.id)
            )

        for summ in self.summaries.list_for_session(session_id):
            out["summaries"].append(
                _Candidate(
                    "summary",
                    summ.content,
                    summ.token_count or self.tokens.count(summ.content),
                    summ.id,
                )
            )

        recent = self.messages.recent_active(session_id, self.recent_keep)
        recent_ids = {m.id for m in recent}
        for m in recent:
            content = f"{m.role}: {m.content}"
            out["recent"].append(
                _Candidate("recent", content, m.token_count or self.tokens.count(content), m.id)
            )

        if query:
            hits = self.retrieval.search(session_id, query, self.top_k)
            for mid, _score in hits:
                if mid in recent_ids:
                    continue  # already in recent; avoid duplication
                msg = self.messages.get(mid)
                if msg is None:
                    continue
                content = f"{msg.role}: {msg.content}"
                out["retrieved"].append(
                    _Candidate(
                        "retrieved",
                        content,
                        msg.token_count or self.tokens.count(content),
                        mid,
                    )
                )

        return out

    def _to_package(
        self, session_id: str, query: str | None, debug: ContextDebug
    ) -> ContextPackage:
        prompt = self._render_prompt(debug.included)
        return ContextPackage(
            session_id=session_id,
            query=query,
            prompt=prompt,
            items=debug.included,
            total_tokens=debug.total_tokens,
            max_tokens=debug.max_tokens,
            sections=debug.sections,
        )

    @staticmethod
    def _render_prompt(items: list[ContextItem]) -> str:
        blocks: dict[str, list[str]] = {}
        for it in items:
            blocks.setdefault(it.source, []).append(it.content)
        parts: list[str] = []
        headers = {
            "memory": "## Known facts about the user",
            "summary": "## Summary of earlier conversation",
            "recent": "## Recent messages",
            "retrieved": "## Relevant earlier messages",
        }
        for source in ["memory", "summary", "retrieved", "recent"]:
            if source in blocks:
                parts.append(headers[source])
                parts.extend(blocks[source])
                parts.append("")
        return "\n".join(parts).strip()

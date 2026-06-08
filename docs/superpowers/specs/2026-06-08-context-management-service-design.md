# Context Management Service — Design Spec

**Date:** 2026-06-08
**Status:** Approved (autonomous build)

## 1. Problem & Goal

A production-grade FastAPI backend that manages conversation context for LLM
applications. It stores sessions/messages, tracks token usage, compresses old
history into summaries, extracts long-term memories, retrieves semantically
relevant history, and assembles a token-budgeted context payload for downstream
LLM calls. Backend only (uvicorn + Swagger); no frontend.

## 2. Key Decisions

| Concern | Choice | Rationale |
|---|---|---|
| Web framework | FastAPI + uvicorn | Required; Swagger at `/docs`. |
| Validation | Pydantic v2 + pydantic-settings | Env-driven config. |
| Relational DB | SQLite (sync SQLAlchemy), `DATABASE_URL`-driven | Zero-service offline default; Postgres = config swap. |
| Vector store | FAISS `IndexIDMap`→`IndexFlatIP`, keyed by `message_id`, persisted to disk | Required choice; in-process, fast. |
| LLM | Local HF `transformers` instruct model (default `Qwen2.5-0.5B-Instruct`), weights baked at build | Offline at runtime. |
| Embeddings | `sentence-transformers` `all-MiniLM-L6-v2` (384-dim) | Offline, fast on CPU. |
| Token counting | The bundled model's HF tokenizer | Consistent, no tiktoken download. |
| Provider abstraction | `LLMProvider` / `EmbeddingProvider` interfaces, real (lazy-import torch) + **fake deterministic** impls | Extensibility + tests never load torch. |

## 3. Architecture (layered)

```
api/routers  →  services  →  repositories  →  SQLAlchemy models + FAISS index
                    ↘ providers (LLM / embedding) ↙
schemas (Pydantic) at the boundary · core/config reads all env vars
```

No layer reaches around the one below it. Dependency wiring via FastAPI
`Depends` + a small app-level singleton container for providers/index.

## 4. Data Model

- **Session**: `id` (uuid str), `title`, `created_at`, `token_count` (running).
- **Message**: `id`, `session_id` (FK), `role` (user|assistant), `content`,
  `token_count`, `created_at`, **`archived`** (bool, default false).
- **Memory**: `id`, `session_id` (FK), `category`, `value`, `created_at`;
  **unique (session_id, category, value)** for dedup.
- **Summary**: `id`, `session_id` (FK), `content`, `covers_from_id`,
  `covers_to_id`, `message_count`, `token_count`, `created_at`.

## 5. Critical reconciliation — compression *soft-archives*, never deletes

Compression sets `archived=True` and **keeps FAISS vectors live**:
- "Recent history" = newest **non-archived** messages.
- Semantic retrieval searches **all** messages (incl. archived) — archived
  content stays reachable.
- A `Summary` covers the archived span. Nothing is lost; the retrieval
  contract holds.

## 6. Where compression runs (deliberate)

Local LLM generation is multi-second on CPU; background jobs are out of scope.
Therefore:
- `POST /messages` only persists + embeds (MiniLM ≈ ms) + updates token_count.
  **Never blocks on the LLM.**
- Compression triggers **lazily at the start of `POST /context/build`** when
  `session.token_count > COMPRESS_TOKEN_THRESHOLD`, and is also exposed via an
  explicit trigger. README documents the latency honestly.

## 7. Context build flow — `POST /context/build` `{session_id, query}`

1. If over threshold → run compression first.
2. Gather candidates:
   - recent **non-archived** messages,
   - stored summaries,
   - memories,
   - FAISS top-k semantically relevant to `query` (over-fetch globally `5×`,
     filter to `session_id`, take top-k).
3. **Token-budget optimizer** allocates `MAX_CONTEXT_TOKENS` across sections by
   priority (memories → summaries → recent → retrieved), truncating gracefully
   and dropping lowest-priority overflow.
4. Return assembled context package + per-section token accounting.

`GET /context/{session_id}` (no query) → **default assembly**: recent +
summaries + memories, **no semantic-retrieval step** (nothing to match
against). Explicitly distinct from the POST builder.

## 8. Memory extraction (tiny-model-tolerant)

Constrained few-shot prompt → **tolerant JSON parsing** (parse failure drops the
fact, never 500s) → dedup via the unique constraint. Categories: `profession`,
`technology`, `preference`, `goal`, `topic`. Runs during compression over the
archived span (off the hot path).

## 9. Token budget optimizer

Given `MAX_CONTEXT_TOKENS` and ordered sections with priorities:
1. Reserve a minimum for `query`.
2. Fill sections in priority order; each item counted via the tokenizer.
3. When a section would overflow, include whole items until the budget is
   exhausted, then stop; record dropped items + reason for the debug endpoint.

## 10. Endpoints

- Sessions: `POST /api/v1/sessions`, `GET /api/v1/sessions`,
  `GET /api/v1/sessions/{id}`, `DELETE /api/v1/sessions/{id}`.
- Messages: `POST /api/v1/messages`, `GET /api/v1/messages/{session_id}`.
- Context: `POST /api/v1/context/build`, `GET /api/v1/context/{session_id}`,
  `GET /api/v1/context/{session_id}/debug` (bonus debug breakdown).
- Memory: `GET /api/v1/memories/{session_id}`.
- Summaries: `GET /api/v1/summaries/{session_id}`,
  `POST /api/v1/summaries/{session_id}/compress` (explicit trigger).
- Health: `GET /health`.

## 11. Housekeeping

- `DELETE /sessions/{id}` cascades DB rows **and** `IndexIDMap.remove_ids` for
  that session's message ids — FAISS stays in sync.
- `GET /health` checks DB connectivity + provider readiness flag.

## 12. Bonus features in scope

- **Token budget optimization algorithm** (§9).
- **Context debugging endpoint** (§10).

Out of scope (noted as future work): Redis, LangGraph, streaming, async DB,
multi-tenant, background jobs.

## 13. Testing

Unit/integration tests using **fake providers** (deterministic hash-based
embeddings + canned extractive LLM) and in-memory SQLite. Cover: session CRUD,
message add + token tracking, memory dedup/parsing, compression
archive-not-delete, budget allocation, retrieval filtering. Fast; no model load.

## 14. Config (env)

`DATABASE_URL`, `FAISS_INDEX_PATH`, `LLM_PROVIDER`, `LLM_MODEL_NAME`,
`EMBEDDING_PROVIDER`, `EMBEDDING_MODEL_NAME`, `EMBEDDING_DIM`,
`MAX_CONTEXT_TOKENS`, `COMPRESS_TOKEN_THRESHOLD`, `RECENT_MESSAGES_KEEP`,
`RETRIEVAL_TOP_K`, `RETRIEVAL_OVERFETCH`, `LOG_LEVEL`.

## 15. Honest cost note

In-process `transformers` makes the image multi-GB and needs ~2–4 GB RAM to
load the model. Tests and the app skeleton run without torch via fake providers;
the real model loads lazily only when `LLM_PROVIDER=local` is exercised.

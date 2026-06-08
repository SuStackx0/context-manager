# Context Management Service

A FastAPI backend that intelligently manages conversation context for LLM
applications. It maintains sessions and messages, tracks token usage, compresses
old history into summaries, extracts long-term memories, retrieves semantically
relevant messages (FAISS), and assembles a token-budgeted context payload for
downstream LLM calls.

## Run

```bash
# Full local model (offline, multi-GB image, ~2-4 GB RAM)
cp .env.example .env
docker compose up --build        # Swagger UI at http://localhost:8000/docs

# Or torch-free with deterministic fake providers (fast)
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
LLM_PROVIDER=fake EMBEDDING_PROVIDER=fake uvicorn app.main:app --reload
```

## Test

```bash
pip install -r requirements-dev.txt
pytest -q        # 20 tests, fake providers, no torch/network
```

## API (under `/api/v1`, plus `/health`)

`sessions` (CRUD) · `messages` (add/list) · `context/build`,
`context/{id}`, `context/{id}/debug` · `memories/{id}` · `summaries/{id}`,
`summaries/{id}/compress`. Full schema at `/docs`.

Design: `docs/superpowers/specs/2026-06-08-context-management-service-design.md`.
Configuration is entirely env-driven — see `.env.example`.

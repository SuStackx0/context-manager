"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.deps import build_singletons
from app.api.routers import (
    context,
    health,
    memories,
    messages,
    sessions,
    summaries,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import init_db

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    logger.info("Starting Context Management Service v%s", __version__)
    init_db()
    app.state.singletons = build_singletons(settings)
    logger.info(
        "Providers ready (llm=%s, embedding=%s)",
        settings.llm_provider,
        settings.embedding_provider,
    )
    yield
    logger.info("Shutting down")


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Context Management Service",
        version=__version__,
        description=(
            "Intelligent conversation context management for LLM apps: "
            "sessions, messages, token tracking, compression/summarization, "
            "memory extraction, semantic retrieval and token-budgeted context."
        ),
        lifespan=lifespan,
    )

    prefix = settings.api_prefix
    app.include_router(sessions.router, prefix=prefix)
    app.include_router(messages.router, prefix=prefix)
    app.include_router(context.router, prefix=prefix)
    app.include_router(memories.router, prefix=prefix)
    app.include_router(summaries.router, prefix=prefix)
    app.include_router(health.router)  # /health (no prefix)

    return app


app = create_app()

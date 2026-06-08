"""Application configuration sourced entirely from environment variables."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All configurable values. Overridable via env vars or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Database
    database_url: str = "sqlite:///./data/context.db"

    # Vector store
    faiss_index_path: str = "./data/faiss.index"

    # Providers: "local" uses the heavy model stack; "fake" is deterministic.
    llm_provider: str = "local"
    llm_model_name: str = "Qwen/Qwen2.5-0.5B-Instruct"
    llm_max_new_tokens: int = 256

    embedding_provider: str = "local"
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_dim: int = 384

    # Token budgeting
    max_context_tokens: int = 2048
    compress_token_threshold: int = 3000
    recent_messages_keep: int = 10
    retrieval_top_k: int = 5
    retrieval_overfetch: int = 5

    # Misc
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()

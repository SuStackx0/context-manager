"""Test fixtures.

Environment is configured for the deterministic *fake* providers and a throwaway
SQLite file BEFORE the app is imported, so tests never load torch/transformers.
"""
from __future__ import annotations

import os
import tempfile

import pytest

# --- Configure env before importing the app -------------------------------
_TMPDIR = tempfile.mkdtemp(prefix="cms_test_")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMPDIR}/test.db"
os.environ["FAISS_INDEX_PATH"] = ""  # empty => in-memory, no persistence
os.environ["LLM_PROVIDER"] = "fake"
os.environ["EMBEDDING_PROVIDER"] = "fake"
os.environ["EMBEDDING_DIM"] = "384"
os.environ["MAX_CONTEXT_TOKENS"] = "100"
os.environ["COMPRESS_TOKEN_THRESHOLD"] = "50"
os.environ["RECENT_MESSAGES_KEEP"] = "2"
os.environ["RETRIEVAL_TOP_K"] = "3"


@pytest.fixture()
def client():
    """A fresh TestClient with a clean database per test."""
    from fastapi.testclient import TestClient

    from app.core.config import get_settings
    from app.db.database import Base, engine
    from app.main import app

    get_settings.cache_clear()
    # Reset schema for isolation.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestClient(app) as c:
        yield c


@pytest.fixture()
def session_id(client) -> str:
    resp = client.post("/api/v1/sessions", json={"title": "test"})
    assert resp.status_code == 201
    return resp.json()["id"]

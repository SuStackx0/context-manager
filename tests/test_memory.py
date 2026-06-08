"""Memory extraction + dedup tests (unit-level, fake LLM)."""
from __future__ import annotations

from app.providers.fake import FakeLLMProvider
from app.repositories.memory_repository import MemoryRepository
from app.services.memory_service import MemoryService


def test_fake_llm_extracts_profession_and_tech():
    llm = FakeLLMProvider()
    prompt = "Extract facts JSON: I work as a QA Engineer and primarily use Python and FastAPI."
    out = llm.generate(prompt)
    assert "QA Engineer" in out
    assert "Python" in out


def test_memory_service_parses_and_dedups(client, session_id):
    # Build a MemoryService on a real DB session via the app's machinery.
    from app.db.database import SessionLocal

    db = SessionLocal()
    try:
        repo = MemoryRepository(db)
        svc = MemoryService(repo, FakeLLMProvider())
        text = "I work as a QA Engineer and primarily use Python and FastAPI."
        first = svc.extract_and_store(session_id, text)
        assert len(first) >= 2
        # Re-running stores nothing new (dedup via unique constraint).
        second = svc.extract_and_store(session_id, text)
        assert second == []
    finally:
        db.close()


def test_parse_tolerates_garbage():
    svc = MemoryService.__new__(MemoryService)  # no deps needed for _parse
    assert svc._parse("not json at all") == []
    assert svc._parse('[{"category":"technology","value":"Python"}]') == [
        ("technology", "Python")
    ]
    # Salvage JSON embedded in prose.
    salvaged = svc._parse('Sure! [{"category":"goal","value":"learn rust"}] done')
    assert salvaged == [("goal", "learn rust")]


def test_memories_endpoint(client, session_id):
    # Drive memory extraction through compression by exceeding the threshold.
    for i in range(6):
        client.post(
            "/api/v1/messages",
            json={
                "session_id": session_id,
                "role": "user",
                "content": "I work as a QA Engineer and use Python and FastAPI daily.",
            },
        )
    client.post(f"/api/v1/summaries/{session_id}/compress")
    resp = client.get(f"/api/v1/memories/{session_id}")
    assert resp.status_code == 200
    cats = {m["category"] for m in resp.json()}
    assert "technology" in cats

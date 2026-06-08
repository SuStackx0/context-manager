"""Context build, compression (soft-archive), and budget tests."""
from __future__ import annotations


def _add(client, sid, content, role="user"):
    return client.post(
        "/api/v1/messages",
        json={"session_id": sid, "role": role, "content": content},
    )


def test_build_context_basic(client, session_id):
    _add(client, session_id, "I love hiking in the mountains")
    _add(client, session_id, "Tell me about trail running", role="assistant")
    resp = client.post(
        "/api/v1/context/build",
        json={"session_id": session_id, "query": "hiking"},
    )
    assert resp.status_code == 200
    pkg = resp.json()
    assert pkg["total_tokens"] <= pkg["max_tokens"]
    assert "sections" in pkg
    assert isinstance(pkg["prompt"], str)


def test_get_default_context_no_query(client, session_id):
    _add(client, session_id, "hello world")
    resp = client.get(f"/api/v1/context/{session_id}")
    assert resp.status_code == 200
    pkg = resp.json()
    assert pkg["query"] is None
    # No retrieved section content when there's no query.
    assert all(it["source"] != "retrieved" for it in pkg["items"])


def test_compression_soft_archives_not_deletes(client, session_id):
    # Exceed the (low) test threshold so compression has work to do.
    for i in range(6):
        _add(client, session_id, f"message number {i} with several words here")

    result = client.post(f"/api/v1/summaries/{session_id}/compress").json()
    assert result["compressed"] is True
    assert result["archived_messages"] >= 1

    # Messages still exist (soft-archive), not deleted.
    msgs = client.get(f"/api/v1/messages/{session_id}").json()
    assert len(msgs) == 6
    assert any(m["archived"] for m in msgs)

    # A summary was stored.
    summaries = client.get(f"/api/v1/summaries/{session_id}").json()
    assert len(summaries) == 1
    assert summaries[0]["message_count"] >= 1


def test_archived_messages_still_retrievable(client, session_id):
    for i in range(6):
        _add(client, session_id, f"distinct topic {i} about astronomy and stars")
    client.post(f"/api/v1/summaries/{session_id}/compress")

    # Semantic retrieval should still surface archived content via debug view.
    resp = client.get(
        f"/api/v1/context/{session_id}/debug", params={"query": "astronomy stars"}
    )
    assert resp.status_code == 200
    debug = resp.json()
    # Either included or considered (dropped) — point is it's reachable.
    reachable = debug["included"] + [
        {"source": d["source"]} for d in debug["dropped"]
    ]
    assert any(item["source"] == "retrieved" for item in reachable) or any(
        s["section"] == "retrieved" and (s["included"] + s["dropped"]) > 0
        for s in debug["sections"]
    )


def test_budget_never_exceeds_max(client, session_id):
    for i in range(20):
        _add(client, session_id, "lots of words " * 10)
    resp = client.post(
        "/api/v1/context/build",
        json={"session_id": session_id, "query": "words"},
    )
    pkg = resp.json()
    assert pkg["total_tokens"] <= pkg["max_tokens"]


def test_debug_reports_sections(client, session_id):
    _add(client, session_id, "alpha beta gamma")
    resp = client.get(
        f"/api/v1/context/{session_id}/debug", params={"query": "alpha"}
    )
    assert resp.status_code == 200
    debug = resp.json()
    section_names = {s["section"] for s in debug["sections"]}
    assert section_names == {"memories", "summaries", "recent", "retrieved"}

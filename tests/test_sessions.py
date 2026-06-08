"""Session CRUD tests."""
from __future__ import annotations


def test_create_and_get_session(client):
    resp = client.post("/api/v1/sessions", json={"title": "demo"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "demo"
    assert data["token_count"] == 0
    sid = data["id"]

    got = client.get(f"/api/v1/sessions/{sid}")
    assert got.status_code == 200
    assert got.json()["id"] == sid


def test_list_sessions(client):
    client.post("/api/v1/sessions", json={"title": "a"})
    client.post("/api/v1/sessions", json={"title": "b"})
    resp = client.get("/api/v1/sessions")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_get_missing_session_404(client):
    assert client.get("/api/v1/sessions/nope").status_code == 404


def test_delete_session(client, session_id):
    assert client.delete(f"/api/v1/sessions/{session_id}").status_code == 204
    assert client.get(f"/api/v1/sessions/{session_id}").status_code == 404


def test_delete_missing_session_404(client):
    assert client.delete("/api/v1/sessions/nope").status_code == 404


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["llm_provider"] == "fake"

"""Message tests."""
from __future__ import annotations


def _add(client, sid, role, content):
    return client.post(
        "/api/v1/messages",
        json={"session_id": sid, "role": role, "content": content},
    )


def test_add_message_tracks_tokens(client, session_id):
    resp = _add(client, session_id, "user", "hello there friend")
    assert resp.status_code == 201
    body = resp.json()
    assert body["token_count"] > 0
    assert body["archived"] is False

    session = client.get(f"/api/v1/sessions/{session_id}").json()
    assert session["token_count"] == body["token_count"]


def test_add_message_unknown_session_404(client):
    assert _add(client, "nope", "user", "hi").status_code == 404


def test_get_messages_ordered(client, session_id):
    _add(client, session_id, "user", "first message")
    _add(client, session_id, "assistant", "second message")
    resp = client.get(f"/api/v1/messages/{session_id}")
    assert resp.status_code == 200
    msgs = resp.json()
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_invalid_role_rejected(client, session_id):
    resp = _add(client, session_id, "robot", "hi")
    assert resp.status_code == 422

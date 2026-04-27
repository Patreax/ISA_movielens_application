"""Cold-path contract tests."""
from __future__ import annotations

import uuid


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_uuid_with_valid_profile_returns_5_descending(client):
    payload = {
        "user_id": _new_uuid(),
        "count": 5,
        "profile": {
            "age_code": 25,
            "gender": "M",
            "occupation_code": 12,
            "preferred_genres": ["Action", "Sci-Fi"],
        },
    }
    resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["path"] == "cold_request_profile"
    assert body["count_requested"] == 5
    assert body["count_returned"] == 5
    recs = body["recommendations"]
    assert len(recs) == 5
    scores = [r["score"] for r in recs]
    for a, b in zip(scores, scores[1:]):
        assert a >= b, f"scores not descending: {scores}"


def test_uuid_without_profile_returns_422(client):
    payload = {"user_id": _new_uuid(), "count": 5}
    resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"] == "validation_error"
    field_errors = body["details"]["field_errors"]
    fields = {fe["field"] for fe in field_errors}
    assert any("profile" in f for f in fields), fields


def test_uuid_with_empty_genres_succeeds(client):
    payload = {
        "user_id": _new_uuid(),
        "count": 5,
        "profile": {
            "age_code": 25,
            "gender": "F",
            "occupation_code": 0,
            "preferred_genres": [],
        },
    }
    resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["path"] == "cold_request_profile"
    assert body["count_returned"] == 5


def test_count_clamped_by_validation_at_100(client):
    """count=200 is rejected by Pydantic ge/le bounds (422), not silently capped."""
    payload = {
        "user_id": _new_uuid(),
        "count": 200,
        "profile": {
            "age_code": 25,
            "gender": "M",
            "occupation_code": 12,
            "preferred_genres": ["Action"],
        },
    }
    resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"] == "validation_error"
    fields = {fe["field"] for fe in body["details"]["field_errors"]}
    assert any("count" in f for f in fields), fields

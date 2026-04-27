"""Request-validation tests (FR-016) — ensure 422 with structured field_errors."""
from __future__ import annotations

import uuid


def _new_uuid() -> str:
    return str(uuid.uuid4())


def test_bad_profile_lists_each_offending_field(client):
    payload = {
        "user_id": _new_uuid(),
        "profile": {
            "age_code": 99,
            "gender": "X",
            "occupation_code": 99,
            "preferred_genres": ["Western", "NotARealGenre"],
        },
    }
    resp = client.post("/recommendations", json=payload)
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"] == "validation_error"
    field_errors = body["details"]["field_errors"]
    fields = {fe["field"] for fe in field_errors}
    assert any("age_code" in f for f in fields), fields
    assert any("gender" in f for f in fields), fields
    assert any("occupation_code" in f for f in fields), fields
    assert any("preferred_genres" in f for f in fields), fields


def test_malformed_user_id_returns_422(client):
    resp = client.post("/recommendations", json={"user_id": "not-an-id", "count": 5})
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["error"] == "validation_error"


def test_zero_user_id_rejected(client):
    resp = client.post("/recommendations", json={"user_id": "0", "count": 5})
    assert resp.status_code == 422, resp.text


def test_negative_user_id_rejected(client):
    resp = client.post("/recommendations", json={"user_id": "-1", "count": 5})
    assert resp.status_code == 422, resp.text

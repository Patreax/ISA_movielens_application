"""Warm-path contract tests."""
from __future__ import annotations


def test_warm_user_returns_5_descending_unrated(client, app_state):
    resp = client.post("/recommendations", json={"user_id": "1", "count": 5})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["path"] == "warm"
    assert body["user_id"] == "1"
    assert body["count_requested"] == 5
    assert body["count_returned"] == 5
    recs = body["recommendations"]
    assert len(recs) == 5

    rated = app_state.user_rated_items.get(1, set())
    for r in recs:
        assert r["movie_id"] not in rated, f"recommendation {r['movie_id']} was rated by user 1"

    scores = [r["score"] for r in recs]
    for a, b in zip(scores, scores[1:]):
        assert a >= b, f"scores not descending: {scores}"

    ranks = [r["rank"] for r in recs]
    assert ranks == [1, 2, 3, 4, 5]


def test_warm_count_defaults_to_10(client):
    resp = client.post("/recommendations", json={"user_id": "1"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["count_requested"] == 10
    assert body["count_returned"] == 10


def test_unknown_integer_user_returns_404(client):
    resp = client.post("/recommendations", json={"user_id": "999999999", "count": 5})
    assert resp.status_code == 404, resp.text
    body = resp.json()
    assert body["error"] == "user_not_found"

"""GET /health contract tests."""
from __future__ import annotations


def test_health_reports_ready_with_loaded_models_and_counts(client):
    resp = client.get("/health")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "ready"
    assert body["models"]["svd"]["loaded"] is True
    assert body["models"]["cold_start"]["loaded"] is True
    assert body["dataset"]["movies"] > 0
    assert body["dataset"]["users"] > 0
    assert body["dataset"]["ratings"] > 0
    assert body["config"]["rating_threshold"] >= 1
    assert body["config"]["data_dir"]
    assert body["config"]["models_dir"]

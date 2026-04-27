"""GET /reference-data contract tests."""
from __future__ import annotations

from recsys_api.constants import AGE_MAP, GENDERS, GENRE_NAMES, OCCUPATION_MAP


def test_reference_data_returns_full_vocabularies(client):
    resp = client.get("/reference-data")
    assert resp.status_code == 200, resp.text
    body = resp.json()

    assert body["genres"] == list(GENRE_NAMES)
    assert len(body["genres"]) == 18

    age_pairs = {(e["code"], e["label"]) for e in body["age_codes"]}
    assert age_pairs == {(c, l) for c, l in AGE_MAP.items()}
    assert len(body["age_codes"]) == 7

    occ_pairs = {(e["code"], e["label"]) for e in body["occupation_codes"]}
    assert occ_pairs == {(c, l) for c, l in OCCUPATION_MAP.items()}
    assert len(body["occupation_codes"]) == 21

    assert body["genders"] == list(GENDERS) == ["M", "F"]

# ISA MovieLens Recommendation API — User Manual

**Audience**: a developer integrating a frontend (or any HTTP client) against
this service. For installation see [`../README.md`](../README.md). For the
canonical machine-readable contract see
[`../../specs/001-movie-recsys-api/contracts/openapi.yaml`](../../specs/001-movie-recsys-api/contracts/openapi.yaml).

The service exposes three endpoints under the same origin (default
`http://localhost:8000`). All requests and responses are JSON over HTTP. No
authentication is required. CORS is enabled (default `*`).

---

## `POST /recommendations`

Returns a ranked list of movie recommendations. The same endpoint serves
both warm (existing MovieLens user) and cold-start (new user) flows; the
service decides which model to use from the request payload.

### Request body

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | Either a positive integer string (existing MovieLens user, e.g. `"1234"`) or a UUID (new user). `"0"` and negative-integer strings are rejected. |
| `count` | integer | no — default `10` | 1 ≤ `count` ≤ 100. |
| `profile` | object | conditional | Required when `user_id` is a UUID. Ignored for warm users (a note is added to the response). |

`profile` shape:

| Field | Type | Notes |
|---|---|---|
| `age_code` | integer | One of `1, 18, 25, 35, 45, 50, 56`. |
| `gender` | string | `"M"` or `"F"`. |
| `occupation_code` | integer | `0..20`. |
| `preferred_genres` | array of string | Subset of the 18 MovieLens-1M genres. May be empty. Duplicates are de-duplicated server-side. |

### Response (HTTP 200)

| Field | Type | Notes |
|---|---|---|
| `user_id` | string | Echoed exactly as supplied. |
| `path` | string | One of `"warm"`, `"cold_request_profile"`, `"cold_stored_demographics"`, `"cold_fallback_genre_popular"`. |
| `count_requested` | integer | The original `count` (or `10` if defaulted). |
| `count_returned` | integer | Actual number of items returned (≤ `count_requested`). |
| `explanation` | string | Human-readable one-liner. |
| `recommendations` | array | Sorted strictly by `score` descending. |
| `notes` | array of string | Informational (may be empty). |

Each recommendation:

| Field | Type | Notes |
|---|---|---|
| `rank` | integer | 1-based position. |
| `movie_id` | integer | MovieLens MovieID. |
| `title` | string | E.g. `"Toy Story (1995)"`. |
| `genres` | array of string | Subset of the 18 MovieLens-1M genres. |
| `score` | number | Predicted rating (warm) or cluster-aggregated score (cold). Treat as opaque; do not assume identical ranges across paths. |

### Error responses

| Status | `error` code | When |
|---|---|---|
| `404` | `user_not_found` | `user_id` is a numeric string but no such MovieLens user exists. |
| `422` | `validation_error` | Bad `user_id`, missing `profile` for a UUID, out-of-range `age_code` / `occupation_code` / `count`, unknown gender or genre. Returns `details.field_errors[]` listing each offending field. |
| `500` | `inference_failed` | The underlying model raised an exception. The payload names the model and the cause. |
| `503` | `service_starting` | Lifespan startup has not yet completed. |

### Examples

**Warm user (existing MovieLens user)**

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{ "user_id": "1", "count": 5 }' | jq
```

```json
{
  "user_id": "1",
  "path": "warm",
  "count_requested": 5,
  "count_returned": 5,
  "explanation": "Recommendations from SVD model for known MovieLens user 1",
  "recommendations": [
    { "rank": 1, "movie_id": 318, "title": "Shawshank Redemption, The (1994)",
      "genres": ["Drama"], "score": 4.81 },
    { "rank": 2, "movie_id": 858, "title": "Godfather, The (1972)",
      "genres": ["Action", "Crime", "Drama"], "score": 4.77 }
  ],
  "notes": []
}
```

**Cold-start user (new UUID)**

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "count": 5,
    "profile": {
      "age_code": 25,
      "gender": "M",
      "occupation_code": 12,
      "preferred_genres": ["Action", "Sci-Fi"]
    }
  }' | jq
```

```json
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "path": "cold_request_profile",
  "count_requested": 5,
  "count_returned": 5,
  "explanation": "Recommendations from cold-start model, similar to cluster 17",
  "recommendations": [
    { "rank": 1, "movie_id": 1196,
      "title": "Star Wars: Episode V - The Empire Strikes Back (1980)",
      "genres": ["Action", "Adventure", "Drama", "Sci-Fi", "War"], "score": 4.55 }
  ],
  "notes": []
}
```

**Validation failure (HTTP 422)**

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "profile": {
      "age_code": 99,
      "gender": "X",
      "occupation_code": 99,
      "preferred_genres": ["Western", "NotARealGenre"]
    }
  }' | jq
```

```json
{
  "error": "validation_error",
  "message": "request validation failed",
  "details": {
    "field_errors": [
      { "field": "profile.age_code",          "message": "Input should be 1, 18, 25, 35, 45, 50 or 56" },
      { "field": "profile.gender",            "message": "Input should be 'M' or 'F'" },
      { "field": "profile.occupation_code",   "message": "Input should be less than or equal to 20" },
      { "field": "profile.preferred_genres",  "message": "unknown genre(s): ['NotARealGenre']" }
    ]
  }
}
```

---

## `GET /health`

Returns liveness + per-model + per-dataset readiness. Suitable for a uptime
probe or a humans-readable smoke check.

```bash
curl -s http://localhost:8000/health | jq
```

```json
{
  "status": "ready",
  "models": {
    "svd":        { "loaded": true },
    "cold_start": { "loaded": true }
  },
  "dataset": {
    "movies": 3883,
    "users":  6040,
    "ratings": 1000209
  },
  "config": {
    "rating_threshold": 5,
    "data_dir": "/app/data/ml-1m",
    "models_dir": "/app/models"
  }
}
```

`status` is `"ready"` once the lifespan handler has finished (models loaded,
self-test passed). It is `"starting"` only during the brief startup window
before lifespan completes.

---

## `GET /reference-data`

Returns the vocabularies the cold-start input controls should use. Use this
endpoint to populate dropdowns in your frontend instead of hard-coding the
lists; the values are guaranteed to match what the cold-start KMeans model
was trained on.

```bash
curl -s http://localhost:8000/reference-data | jq
```

```json
{
  "genres": ["Action", "Adventure", "Animation", "Children's", "...", "Western"],
  "age_codes": [
    { "code": 1,  "label": "Under 18" },
    { "code": 18, "label": "18-24" },
    { "code": 25, "label": "25-34" },
    { "code": 35, "label": "35-44" },
    { "code": 45, "label": "45-49" },
    { "code": 50, "label": "50-55" },
    { "code": 56, "label": "56+" }
  ],
  "occupation_codes": [
    { "code": 0,  "label": "other" },
    { "code": 1,  "label": "academic/educator" },
    { "code": 12, "label": "programmer" }
  ],
  "genders": ["M", "F"]
}
```

The response is static across the process lifetime; you may cache it client-side.

---

## OpenAPI / Swagger

The service auto-publishes the OpenAPI spec at:

- `GET /openapi.json` — raw spec
- `GET /docs`         — Swagger UI
- `GET /redoc`        — ReDoc

Use these for ad-hoc exploration and code generation.

---

## Routing rules at a glance

| `user_id` shape | rating count | `profile` supplied? | Resulting path |
|---|---|---|---|
| positive integer (known) | ≥ threshold | (ignored) | `warm` |
| positive integer (known) | < threshold | (ignored) | `cold_stored_demographics` |
| positive integer (unknown) | n/a | n/a | HTTP 404 `user_not_found` |
| UUID | n/a | yes | `cold_request_profile` |
| UUID | n/a | no | HTTP 422 `validation_error` |

The threshold is `RECSYS_API_RATING_THRESHOLD` (default `5`). All three cold
paths fall back to `cold_fallback_genre_popular` if the matched cluster has
no users (research.md D-08, FR-017).

---

## Limits & guarantees

- **Stateless.** No session, no cookies, no per-user storage. Two identical
  requests return identical results within the lifetime of a process.
- **Single-process, in-memory.** Models and reference data are loaded once
  at startup; `/health` confirms that. There is no degraded mode.
- **Latency.** Both paths return in under 2 seconds on the demo machine for
  the full MovieLens-1M dataset.
- **No retraining.** This service only loads pretrained `.pkl` artefacts;
  training lives in the source recsys repo (Constitution Principle IV).

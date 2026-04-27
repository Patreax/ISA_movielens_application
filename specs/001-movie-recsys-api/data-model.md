# Phase 1 — Data Model: Movie Recommendation REST API Backend

**Feature**: 001-movie-recsys-api
**Date**: 2026-04-27
**Plan**: [plan.md](./plan.md) | **Spec**: [spec.md](./spec.md)

The service has **no persistent storage**. Everything below describes the data structures that live in process memory and the wire-level entities that move across the REST boundary.

---

## In-memory state (loaded once at startup)

The service holds a single `AppState` value, built by the lifespan handler and shared with every endpoint via FastAPI dependency injection. All fields are read-only after startup.

### `AppState`

| Field | Type | Source | Purpose |
|---|---|---|---|
| `config` | `Settings` | env vars | Tunables (paths, threshold, port, CORS, log level). See research.md D-11. |
| `movies` | `pandas.DataFrame` | `movies.dat` | Index by row, columns: `item_id` (int), `title` (str), `genres_str` (str), plus 18 binary genre columns matching `GENRE_NAMES`. |
| `users` | `pandas.DataFrame` | `users.dat` | Indexed by `user_id` (int) for O(1) lookup. Columns: `gender` ∈ {"M","F"}, `age_code` ∈ {1,18,25,35,45,50,56}, `occupation_code` ∈ 0..20, `zip_code`, plus derived `age_label`, `occupation`. |
| `ratings` | `pandas.DataFrame` | `ratings.dat` | Columns: `user_id`, `item_id`, `rating` (1..5), `timestamp`. |
| `svd_model` | `surprise.SVD` | `svd_model.pkl` | Fitted matrix-factorisation model; `predict(user_id_str, item_id_str)` returns a `Prediction` whose `est` field is the score. |
| `cold_start_model` | `dict` | `cold_start_model.pkl` | Keys: `kmeans` (sklearn `KMeans`), `scaler` (sklearn `StandardScaler`), `encoders` (dict with `gender` → `LabelEncoder`), `user_features` (`DataFrame` indexed by `user_id`, columns include the scaled features and a `cluster` column). |
| `known_user_ids` | `set[int]` | derived from `users` | Membership check for the routing rule (FR-005). |
| `rating_counts` | `dict[int, int]` | derived from `ratings.groupby("user_id").size()` | Threshold check for FR-005. |
| `user_rated_items` | `dict[int, set[int]]` | derived from `ratings.groupby("user_id")["item_id"].apply(set)` | Used to filter "do not recommend movies the user already rated" (FR-014). |
| `all_item_ids` | `list[int]` | `movies["item_id"].tolist()` | Candidate set for warm-path scoring. |
| `title_by_item` | `dict[int, str]` | `movies.set_index("item_id")["title"].to_dict()` | O(1) title lookup for the response. |
| `genres_by_item` | `dict[int, list[str]]` | `movies` genre columns | O(1) genre list lookup for the response. |

**Invariants:**

- `set(known_user_ids) == set(users.index) == set(rating_counts) == set(user_rated_items)`.
- Every `user_id` that appears in `ratings` is present in `users` (true for MovieLens-1M).
- `cold_start_model["user_features"].index.intersection(known_user_ids) == known_user_ids` (the cold-start model was trained on the same user set).
- The 18 genre column names in `movies` exactly match the constant `GENRE_NAMES`.
- Throughout the process lifetime, none of these structures are mutated.

**Validation at load time** (raises `RuntimeError`, blocking startup, satisfying Constitution III):

- `svd_model` is an instance of `surprise.prediction_algorithms.matrix_factorization.SVD`.
- `cold_start_model` has all four expected keys; `kmeans` is a `KMeans`; `scaler` is a `StandardScaler`; `encoders["gender"]` is a `LabelEncoder`; `user_features` is a `DataFrame` with a `cluster` column.
- All three `.dat` files yield non-empty DataFrames of the expected column shape.

---

## Reference vocabularies (constants)

These constants are the source of truth for cold-start input validation (FR-008) and for the `/reference-data` endpoint (FR-020). They are copied verbatim from `project1.dataset` (research.md D-07).

### `GENRE_NAMES` — 18 entries, exact strings

```text
Action, Adventure, Animation, Children's, Comedy, Crime, Documentary, Drama,
Fantasy, Film-Noir, Horror, Musical, Mystery, Romance, Sci-Fi, Thriller, War, Western
```

### `AGE_MAP` — 7 brackets

| code | label |
|---|---|
| 1  | Under 18 |
| 18 | 18-24 |
| 25 | 25-34 |
| 35 | 35-44 |
| 45 | 45-49 |
| 50 | 50-55 |
| 56 | 56+ |

### `OCCUPATION_MAP` — 21 codes

| code | label |
|---|---|
| 0 | other |
| 1 | academic/educator |
| 2 | artist |
| 3 | clerical/admin |
| 4 | college/grad student |
| 5 | customer service |
| 6 | doctor/health care |
| 7 | executive/managerial |
| 8 | farmer |
| 9 | homemaker |
| 10 | K-12 student |
| 11 | lawyer |
| 12 | programmer |
| 13 | retired |
| 14 | sales/marketing |
| 15 | scientist |
| 16 | self-employed |
| 17 | technician/engineer |
| 18 | tradesman/craftsman |
| 19 | unemployed |
| 20 | writer |

### `GENDER` — 2 values

```text
M, F
```

---

## Wire entities (request/response)

The wire shapes below are normative. The OpenAPI document at `contracts/openapi.yaml` is the canonical machine-readable form; the prose here exists for the human reviewer.

### `RecommendationRequest` (POST /recommendations body)

| Field | Type | Required | Notes |
|---|---|---|---|
| `user_id` | string | yes | Either a positive integer in string form (e.g. `"1234"` — known MovieLens user) or a UUID string (RFC 4122). Numeric strings are interpreted as MovieLens IDs (FR-010). |
| `count` | integer | no, default 10 | 1 ≤ count ≤ 100 (FR-009). |
| `profile` | `ColdStartProfile` | conditional | Required iff routing decides "cold with request demographics" (research.md D-05). May be supplied harmlessly in the warm case (ignored, with an info note in the response). |

**Validation rules:**

- `user_id` must be either parseable as a positive integer **or** a syntactically valid UUID; otherwise 422.
- `count` outside `[1, 100]` ⇒ 422 with field name and accepted range.
- If routing requires `profile` and it is missing or malformed ⇒ 422 with the offending fields named (FR-016).

### `ColdStartProfile`

| Field | Type | Required | Notes |
|---|---|---|---|
| `age_code` | integer | yes | Must be in `{1, 18, 25, 35, 45, 50, 56}`. |
| `gender` | string | yes | Must be `"M"` or `"F"`. |
| `occupation_code` | integer | yes | Must be in `[0, 20]`. |
| `preferred_genres` | `list[string]` | yes | Each element must be in `GENRE_NAMES`. May be empty. Duplicates are de-duplicated server-side. |

### `MovieRecommendation` (single item in the response list)

| Field | Type | Notes |
|---|---|---|
| `rank` | integer | 1-based position in the returned list. |
| `movie_id` | integer | MovieLens MovieID. |
| `title` | string | From `movies.dat`, latin-1 decoded. |
| `genres` | `list[string]` | Genre names this movie carries (subset of `GENRE_NAMES`). |
| `score` | number | Predicted rating (warm path, ~1.0–5.0 range from SVD) or popularity-weighted average rating from cluster (cold path, ~1.0–5.0). The frontend MUST treat this as an opaque sortable score; the contract does not promise a single normalised range across paths. |

### `RecommendationResponse` (POST /recommendations 200 body)

| Field | Type | Notes |
|---|---|---|
| `user_id` | string | Echoed back exactly as supplied. |
| `path` | string | One of `"warm"`, `"cold_request_profile"`, `"cold_stored_demographics"`, `"cold_fallback_genre_popular"`. The fourth value indicates the cold-start model's documented fallback (FR-017) was used. |
| `count_requested` | integer | The original `count` (or 10 if defaulted). |
| `count_returned` | integer | Actual number of items in `recommendations`. May be less than requested per FR-015. |
| `explanation` | string | Human-readable one-liner suitable for the frontend (FR-013). Examples: `"Recommendations from SVD model for known MovieLens user 1234"`, `"Recommendations from cold-start model, similar to cluster 17"`, `"Cold-start fallback: most popular movies in your preferred genres"`. |
| `recommendations` | `list[MovieRecommendation]` | Sorted strictly by `score` descending (FR-014). |
| `notes` | `list[string]` | Optional informational messages (e.g. `"profile field was supplied but ignored because user_id is a known MovieLens user"`, `"requested 50 but only 12 unrated movies remain for this user"`). Empty list when there is nothing to report. |

### `HealthResponse` (GET /health 200 body)

| Field | Type | Notes |
|---|---|---|
| `status` | string | `"ready"` once lifespan startup has completed; `"starting"` if lifespan has not finished (rare; lifespan is awaited before serving). |
| `models` | object | `{"svd": {"loaded": bool}, "cold_start": {"loaded": bool}}`. |
| `dataset` | object | `{"movies": int, "users": int, "ratings": int}` — row counts. |
| `config` | object | `{"rating_threshold": int, "data_dir": str, "models_dir": str}`. |

### `ReferenceDataResponse` (GET /reference-data 200 body)

| Field | Type | Notes |
|---|---|---|
| `genres` | `list[string]` | Exactly `GENRE_NAMES`. |
| `age_codes` | `list[{code: int, label: string}]` | The 7 age brackets. |
| `occupation_codes` | `list[{code: int, label: string}]` | The 21 occupations. |
| `genders` | `list[string]` | `["M", "F"]`. |

### `ErrorResponse` (4xx and 5xx body)

| Field | Type | Notes |
|---|---|---|
| `error` | string | Short machine-readable identifier, e.g. `"validation_error"`, `"user_not_found"`, `"inference_failed"`, `"service_starting"`. |
| `message` | string | Human-readable summary. |
| `details` | object | Optional structured detail. For validation errors: `{"field_errors": [{"field": "...", "message": "...", "accepted": [...]}]}`. |

---

## Routing decision (textual contract)

```text
INPUT:  RecommendationRequest, AppState
OUTPUT: one of: ("warm", user_id_int)
              | ("cold_stored", user_id_int)
              | ("cold_request",)
        plus a list of "notes" entries

if user_id parses as positive integer K:
    if K in known_user_ids:
        if rating_counts[K] >= rating_threshold:
            if profile is not None: notes.append("profile ignored: known warm user")
            return ("warm", K)
        else:
            if profile is not None: notes.append("profile ignored: stored demographics used")
            return ("cold_stored", K)
    else:
        return error: user_not_found (404)
elif user_id is a valid UUID:
    if profile is None:
        return error: validation_error, profile required (422)
    return ("cold_request",)
else:
    return error: validation_error, malformed user_id (422)
```

This logic lives in `recsys_api.routing.decide_path`. The error returns map to the OpenAPI 4xx responses.

---

## State transitions

The application has exactly two states:

```text
[ uninitialised ]
        │
        │  lifespan startup
        │  (load files, load models, derive caches, run self-test)
        ▼
[ ready ] ──────────────► serves requests until SIGTERM ──────────────► [ uninitialised ]
                                                                            (lifespan
                                                                             shutdown,
                                                                             which
                                                                             only logs)
```

Failure during `lifespan startup` ⇒ process exits non-zero (Constitution III). There is no "degraded" state.

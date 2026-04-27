# Code Walkthrough — ISA MovieLens Recommendation API

A guided tour of the `backend/` codebase for someone new to FastAPI / Python
backend services. Follow the sections in order; each one builds on the
previous. Total reading time: ~30 minutes.

By the end you should be able to answer: "Where does an HTTP request land,
how does it travel through the code, and where do I make a change to add
a new field / endpoint / validation rule?"

---

## Table of contents

1. [What FastAPI is, in one paragraph](#1-what-fastapi-is-in-one-paragraph)
2. [The big picture](#2-the-big-picture)
3. [Project layout](#3-project-layout)
4. [Recommended reading order](#4-recommended-reading-order)
5. [The startup flow (lifespan)](#5-the-startup-flow-lifespan)
6. [A warm request end-to-end](#6-a-warm-request-end-to-end)
7. [A cold request end-to-end](#7-a-cold-request-end-to-end)
8. [Module-by-module reference](#8-module-by-module-reference)
9. [How the test suite works](#9-how-the-test-suite-works)
10. [Common modifications: where do I change X?](#10-common-modifications-where-do-i-change-x)
11. [Glossary of FastAPI / Python concepts used here](#11-glossary-of-fastapi--python-concepts-used-here)

---

## 1. What FastAPI is, in one paragraph

**FastAPI** is a Python web framework. You declare your endpoints as Python
functions with type-annotated parameters; FastAPI inspects those annotations,
auto-generates request validation (via [Pydantic](https://docs.pydantic.dev/))
and an OpenAPI/Swagger document, and routes incoming HTTP requests to your
functions. It runs on top of **Uvicorn**, an ASGI server (the modern Python
equivalent of Gunicorn for async apps). For us, the pipeline is:

```
HTTP client  →  Uvicorn (ASGI server)  →  FastAPI app  →  your endpoint function
                                              ↓
                                  Pydantic validates request body
                                              ↓
                                  Your function returns a Pydantic model
                                              ↓
                                  FastAPI serialises to JSON, returns it
```

You never write the JSON parsing, the OpenAPI spec, or the type validation
yourself. You write **schemas** (Pydantic models) and **endpoints**
(decorated functions); FastAPI does the rest.

---

## 2. The big picture

Our service has exactly **three responsibilities**:

1. **Load** two pretrained ML models (`svd_model.pkl`, `cold_start_model.pkl`)
   and the MovieLens-1M reference data into memory **once**, at startup.
2. **Route** each `POST /recommendations` request to one of two inference
   helpers based on the user's identity (warm vs cold).
3. **Serve** that result — plus two read-only endpoints (`/health`,
   `/reference-data`) — as JSON.

There is **no database**, no auth, no background jobs, no message queue.
Every request is stateless. Two identical requests return identical
responses for the lifetime of a process.

ASCII view of the running process:

```
┌────────────────────────────────────────────────────────────────────┐
│  Uvicorn (port 8000)                                               │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FastAPI app (recsys_api.main:app)                           │  │
│  │  ┌────────────────────────────────────────────────────────┐  │  │
│  │  │  CORS middleware                                       │  │  │
│  │  ├────────────────────────────────────────────────────────┤  │  │
│  │  │  Exception handlers (errors.py)                        │  │  │
│  │  │   • UserNotFoundError    → 404 user_not_found          │  │  │
│  │  │   • InferenceError       → 500 inference_failed        │  │  │
│  │  │   • ServiceStartingError → 503 service_starting        │  │  │
│  │  │   • RequestValidationError → 422 + field_errors        │  │  │
│  │  ├────────────────────────────────────────────────────────┤  │  │
│  │  │  Routers:                                              │  │  │
│  │  │   • POST /recommendations    (api/recommend.py)        │  │  │
│  │  │   • GET  /health             (api/health.py)           │  │  │
│  │  │   • GET  /reference-data     (api/reference.py)        │  │  │
│  │  └────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                              ▲                                     │
│                              │ Depends(get_app_state)              │
│                              │                                     │
│                ┌─────────────┴─────────────────┐                   │
│                │ AppState (state.py) — frozen   │                  │
│                │  • movies / users / ratings DataFrames           │
│                │  • svd_model (surprise.SVD)                      │
│                │  • cold_start_model (dict of sklearn objects)    │
│                │  • derived caches (rated_items, title_by_item …) │
│                └────────────────────────────────────────────────┐ │
│                              ▲                                  │ │
│                              │ built once by lifespan handler   │ │
│                              │ at startup (main.py::lifespan)   │ │
│                              │                                  │ │
│                  ┌───────────┴───────────┐                      │ │
│                  │ data_loader.py        │   model_loader.py    │ │
│                  │  reads .dat files     │   pickle.load+verify │ │
│                  └───────────────────────┘   └──────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

Two important properties to internalise:

- **Read-only after startup.** The `AppState` object is built once and never
  mutated. Every request reads from the same in-memory snapshot.
- **No degraded mode.** If startup loading or the self-test fails, Uvicorn
  exits non-zero. The service is either fully ready or not running.

---

## 3. Project layout

```text
backend/
├── Dockerfile                     # Single-stage Python 3.12-slim image
├── requirements.txt               # Pinned runtime deps (Constitution IV)
├── requirements-dev.txt           # +pytest, httpx, ruff
├── pyproject.toml                 # Package metadata + ruff/pytest config
├── README.md                      # Installation manual
├── docs/
│   ├── user-manual.md             # Endpoint reference for API consumers
│   ├── quality-and-risk.md        # Assignment 3.1.C content
│   └── code-walkthrough.md        # ← this file
├── scripts/
│   └── copy-assets.sh             # One-shot copy of .pkl + .dat from source repo
├── data/ml-1m/                    # movies.dat, users.dat, ratings.dat (gitignored)
├── models/                        # svd_model.pkl, cold_start_model.pkl (gitignored)
├── src/
│   └── recsys_api/                # The actual Python package
│       ├── __init__.py
│       ├── main.py                # FastAPI app factory + lifespan handler
│       ├── config.py              # Settings (env-var-driven)
│       ├── constants.py           # GENRE_NAMES, AGE_MAP, OCCUPATION_MAP, GENDERS
│       ├── schemas.py             # Pydantic wire models (request/response shapes)
│       ├── data_loader.py         # Read MovieLens .dat files into DataFrames
│       ├── model_loader.py        # pickle.load + structural validation
│       ├── state.py               # AppState dataclass + build_state() factory
│       ├── routing.py             # decide_path(): warm vs cold
│       ├── features.py            # encode_cold_user() — cold-start vector encoder
│       ├── errors.py              # Custom exceptions + FastAPI exception handlers
│       ├── self_test.py           # Startup smoke test (one warm + one cold inference)
│       ├── api/
│       │   ├── __init__.py
│       │   ├── recommend.py       # POST /recommendations
│       │   ├── health.py          # GET  /health
│       │   └── reference.py       # GET  /reference-data
│       └── inference/
│           ├── __init__.py
│           ├── warm.py            # SVD top-N for known users
│           └── cold.py            # Cluster-aggregation for new users
└── tests/
    ├── conftest.py                # Shared fixtures (AppState, TestClient)
    ├── test_recommend_warm.py
    ├── test_recommend_cold.py
    ├── test_validation.py
    ├── test_health.py
    └── test_reference.py
```

Two conventions worth noting:

- **`src/` layout.** The package lives under `src/recsys_api/` rather than at
  `backend/recsys_api/`. This is a common Python convention that prevents
  accidental imports of the source tree without installing the package
  (it forces tests to use `PYTHONPATH=src`, surfacing setup mistakes early).
- **One file = one concern.** Each module has one job (loader, schemas,
  routing, etc.). Endpoints under `api/` are thin: they only orchestrate;
  the actual work lives in `inference/` or pure functions like
  `routing.decide_path`.

---

## 4. Recommended reading order

Read the files in this order. Each builds on the previous and you can stop
at any point with a working mental model up to that point.

| Step | File | What you learn |
|---|---|---|
| 1 | [`constants.py`](../src/recsys_api/constants.py) | The three vocabularies (genres, ages, occupations) — these recur everywhere. |
| 2 | [`schemas.py`](../src/recsys_api/schemas.py) | The wire shapes (request/response). This *is* the API contract in code. |
| 3 | [`config.py`](../src/recsys_api/config.py) | How env vars become a `Settings` object. |
| 4 | [`data_loader.py`](../src/recsys_api/data_loader.py) | Reading the three `.dat` files. |
| 5 | [`model_loader.py`](../src/recsys_api/model_loader.py) | `pickle.load` + structural assertions. |
| 6 | [`state.py`](../src/recsys_api/state.py) | The `AppState` dataclass that ties (1)-(5) together. |
| 7 | [`main.py`](../src/recsys_api/main.py) | The FastAPI app factory and the **lifespan handler** (the most important file). |
| 8 | [`routing.py`](../src/recsys_api/routing.py) | The single `if/else` that picks warm vs cold. |
| 9 | [`inference/warm.py`](../src/recsys_api/inference/warm.py) | SVD prediction loop. |
| 10 | [`inference/cold.py`](../src/recsys_api/inference/cold.py) | Cluster aggregation. |
| 11 | [`api/recommend.py`](../src/recsys_api/api/recommend.py) | The endpoint that orchestrates 8-10. |
| 12 | [`api/health.py`](../src/recsys_api/api/health.py), [`api/reference.py`](../src/recsys_api/api/reference.py) | The two read-only endpoints. Trivial. |
| 13 | [`errors.py`](../src/recsys_api/errors.py) | How exceptions become JSON error responses. |
| 14 | [`self_test.py`](../src/recsys_api/self_test.py) | The startup canary that prevents serving with bad models. |
| 15 | [`tests/conftest.py`](../tests/conftest.py) and one test file | How we test against the real models with `TestClient`. |

---

## 5. The startup flow (lifespan)

This is the most important concept in the codebase. Read it twice.

When Uvicorn imports `recsys_api.main:app`, three things happen in order:

### 5.1 Module-level setup (instant)

```python
# main.py — last line
app = create_app()
```

`create_app()` builds a `FastAPI` instance, attaches CORS middleware,
registers the four exception handlers, and includes the three routers. It
**does not load any models or data yet** — that's deferred to the lifespan
handler. At this point the app object exists but `app.state.app_state` is
unset.

### 5.2 Lifespan startup (the slow bit, ~10 s)

When Uvicorn starts serving requests, FastAPI calls our `lifespan` async
context manager (declared in `main.py`):

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    state = build_state(settings)         # ← reads .dat + .pkl, derives caches
    app.state.app_state = state           # ← stash it on the app object
    run_startup_self_test(state)          # ← one warm + one cold inference
    yield                                 # ← service is now serving requests
    # (anything after `yield` runs at shutdown — we just log)
```

`build_state(settings)` (in `state.py`) does the heavy lifting:

```
build_state(settings)
  ├── load_movies(data_dir/"movies.dat")         → pandas DataFrame
  ├── load_users(data_dir/"users.dat")           → pandas DataFrame
  ├── load_ratings(data_dir/"ratings.dat")       → pandas DataFrame
  ├── load_svd(models_dir/"svd_model.pkl")       → surprise.SVD (with type assert)
  ├── load_cold_start(models_dir/"cold_start_model.pkl") → dict (with key/type asserts)
  └── derive caches: known_user_ids, rating_counts, user_rated_items,
                     all_item_ids, title_by_item, genres_by_item
```

Then `run_startup_self_test(state)`:

- Calls `recommend_warm(state, user_id_int=1, count=5)` and asserts the
  result is 5 movies, descending scores, none in user 1's rated set.
- Calls `recommend_cold_with_profile(state, age=25, gender="M",
  occ=12, genres=["Action", "Sci-Fi"], count=5)` and asserts the same.
- Either failure raises `RuntimeError`, which propagates up through the
  lifespan handler. Uvicorn's lifespan-failure path causes the process to
  exit non-zero — the container restarts (or simply fails) instead of
  serving with a broken model.

### 5.3 Serving (forever, until SIGTERM)

After `yield`, every incoming request can access the prebuilt state via:

```python
def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state
```

This is FastAPI's standard "share state across requests" pattern.
`request.app` is the `FastAPI` instance, `app.state` is a free-form
namespace, and we stuck our `AppState` dataclass on it during lifespan.

### Why a context manager?

FastAPI used to have `@app.on_event("startup")` and `@app.on_event("shutdown")`
decorators. They worked but couldn't share state between startup and
shutdown without globals. The `@asynccontextmanager` form is the modern
replacement: code before `yield` is "startup", code after is "shutdown",
and they share local variables naturally.

---

## 6. A warm request end-to-end

Let's trace `POST /recommendations` with body `{"user_id": "1", "count": 5}`.

### Step 1 — Uvicorn → FastAPI

Uvicorn parses the HTTP request, creates an ASGI scope, and hands it to the
FastAPI app object.

### Step 2 — Middleware

The CORS middleware (registered in `main.create_app()`) inspects the
`Origin` header. For us with `allow_origins=["*"]` it adds the appropriate
`Access-Control-Allow-*` headers and lets the request through.

### Step 3 — Routing

FastAPI looks up `POST /recommendations` in its router table and finds
`post_recommendations` in `api/recommend.py`.

### Step 4 — Request validation (Pydantic)

The endpoint signature is:

```python
async def post_recommendations(
    payload: RecommendationRequest,
    state: AppState = Depends(_get_state),
) -> RecommendationResponse:
```

FastAPI sees `payload: RecommendationRequest` and:

1. Reads the request body as JSON.
2. Calls `RecommendationRequest.model_validate(json_body)`.
3. If validation fails (bad type, missing required field, custom validator
   raises) — Pydantic raises `RequestValidationError`, our handler in
   `errors.py` catches it and returns 422 with `details.field_errors`.
4. If validation succeeds, `payload` is now a typed Python object:
   `payload.user_id == "1"`, `payload.count == 5`, `payload.profile is None`.

`Depends(_get_state)` is FastAPI's **dependency injection** — it calls
`_get_state(request)` (defined in the same file) and passes the result as
the `state` argument. `_get_state` reads `request.app.state.app_state` and
either returns it or raises `ServiceStartingError`.

### Step 5 — Routing decision

```python
decision = decide_path(payload, state)
```

`decide_path` (in `routing.py`) implements the rule from `data-model.md`:

```
"1" is digits → uid_int = 1
1 in known_user_ids? → yes
rating_counts[1] >= 5 (threshold)? → yes (user 1 has 53 ratings)
→ RoutingDecision(kind="warm", user_id_int=1, notes=())
```

### Step 6 — Inference

```python
recs = recommend_warm(state, decision.user_id_int, payload.count)
```

`recommend_warm` (in `inference/warm.py`) does:

```python
rated = state.user_rated_items[1]      # set of item_ids user 1 already rated
for item_id in state.all_item_ids:     # ~3883 movies
    if item_id in rated: continue
    pred = state.svd_model.predict("1", str(item_id))  # surprise.SVD call
    scored.append((item_id, pred.est))
scored.sort(key=lambda x: x[1], reverse=True)
top = scored[:5]
return [MovieRecommendation(rank=i+1, movie_id=..., title=..., genres=..., score=...)
        for i, (item_id, score) in enumerate(top)]
```

Roughly 0.3-0.6 s on the demo machine; the loop is the bulk.

### Step 7 — Response building

The endpoint wraps the result in a `RecommendationResponse`:

```python
return RecommendationResponse(
    user_id="1", path="warm", count_requested=5, count_returned=5,
    explanation="Recommendations from SVD model for known MovieLens user 1",
    recommendations=recs, notes=[],
)
```

### Step 8 — Serialisation

FastAPI sees the function returns a `RecommendationResponse` (declared in
the `response_model=`). It calls `.model_dump_json()` on the object,
returns HTTP 200 with `Content-Type: application/json`.

End-to-end: one Python function call per HTTP request, ~0.5 s, no I/O
beyond the network.

---

## 7. A cold request end-to-end

For `POST /recommendations` with body
`{"user_id": "<UUID>", "count": 5, "profile": {age_code: 25, gender: "M",
occupation_code: 12, preferred_genres: ["Action", "Sci-Fi"]}}`:

Steps 1-4 same as above. Note that Pydantic recursively validates the
nested `profile` object against `ColdStartProfile` and rejects any
out-of-range field with a precise message.

### Step 5 — Routing decision

```
"550e8400-…" is not digits → try UUID parse → succeeds
profile is not None → ok
→ RoutingDecision(kind="cold_request")
```

### Step 6 — Cold inference

```python
recs, path_value, explanation, cold_notes = recommend_cold_with_profile(
    state,
    age_code=25, gender="M", occupation_code=12,
    preferred_genres=["Action", "Sci-Fi"], count=5,
)
```

`recommend_cold_with_profile` (in `inference/cold.py`):

1. `encode_cold_user(...)` → 21-element vector matching what the cold-start
   KMeans was trained on (3 demographics + 18 genre preferences, scaled).
2. `kmeans.predict([vec])[0]` → cluster id (e.g. 17).
3. Filter `user_features` DataFrame to that cluster's users.
4. Slice `state.ratings` to those users' high (≥ 4) ratings.
5. Group by `item_id`, compute mean rating + count.
6. Boost +0.5 for movies in the user's preferred genres.
7. Sort, take top-N, return as `MovieRecommendation` list.

### Step 7-8 — Response

Same shape as warm, but `path == "cold_request_profile"` and the
`explanation` includes the cluster id.

---

## 8. Module-by-module reference

Quick reference; one paragraph each.

### `constants.py`

The three reference vocabularies (`GENRE_NAMES`, `AGE_MAP`, `OCCUPATION_MAP`,
`GENDERS`). Copied verbatim from the source recsys repo's `project1.dataset`
because the cold-start KMeans was trained against these exact values — any
divergence silently corrupts predictions.

### `schemas.py`

Every shape that crosses the HTTP boundary. Two notable techniques:

- **`Literal[...]` and `Enum` types** for closed-set fields (`age_code`,
  `gender`, `path`). Pydantic auto-rejects values outside the set.
- **`@field_validator`** decorators for custom rules — e.g. `user_id` must
  be a positive-integer string OR a UUID; `preferred_genres` must be a
  subset of `GENRE_NAMES`.
- **`ConfigDict(extra="forbid")`** rejects unknown fields with 422 instead
  of silently ignoring them.

This file *is* the API contract; if you change a field here you've changed
the public API.

### `config.py`

A `Settings(BaseSettings)` class from
[`pydantic-settings`](https://docs.pydantic.dev/latest/concepts/pydantic_settings/).
Each attribute is read from a `RECSYS_API_*` env var (e.g.
`rating_threshold` ← `RECSYS_API_RATING_THRESHOLD`); defaults are inline.
The `get_settings()` function is `@lru_cache`d so the parsing cost is paid
once.

### `data_loader.py`

Three `load_*` functions, one per `.dat` file. Each is a thin wrapper
around `pd.read_csv(sep="::", encoding="latin-1", engine="python")` that
matches the source recsys repo's parsers exactly. `load_movies` also
expands the pipe-separated genres into 18 binary columns (one per genre)
because the rest of the code prefers that shape.

### `model_loader.py`

`load_svd` and `load_cold_start`. Both `pickle.load` the file and then
**assert structure**:

- `load_svd` checks `isinstance(obj, surprise.SVD)`.
- `load_cold_start` checks the dict has the four required keys, each of the
  expected sklearn type, and that `user_features` has a `cluster` column.

These asserts are how we honour Constitution III ("no degraded startup"):
if a future `.pkl` file is structurally wrong we fail at boot rather than
producing weird recommendations.

### `state.py`

A `@dataclass` called `AppState` plus a `build_state(settings)` factory.
The factory calls the loaders, then derives small lookup caches:

- `known_user_ids: set[int]` — for O(1) membership tests in routing.
- `rating_counts: dict[int, int]` — for the threshold check.
- `user_rated_items: dict[int, set[int]]` — to skip movies a user already saw.
- `title_by_item`, `genres_by_item` — to populate response fields without
  scanning the DataFrame on every recommendation.

Once built, `AppState` is treated as immutable; nothing in the codebase
mutates it.

### `main.py`

The FastAPI app factory + lifespan handler. Three things to remember:

1. `create_app()` is the factory — it builds an empty FastAPI, adds CORS,
   registers exception handlers, includes routers. **No I/O.**
2. `lifespan(app)` runs once when Uvicorn starts; it loads everything,
   stashes `AppState` on `app.state`, runs the self-test, then `yield`s.
3. `app = create_app()` at module scope — this is the variable Uvicorn
   imports via `uvicorn recsys_api.main:app`.

### `routing.py`

A single function `decide_path(req, state)` that returns a frozen
`RoutingDecision(kind, user_id_int, notes)`. `kind` is one of `"warm"`,
`"cold_stored"`, `"cold_request"`. Encapsulates the entire warm-vs-cold
rule in one place — the recommend router never duplicates this logic.

### `features.py`

`encode_cold_user(...)` — adapts the source recsys repo's profile encoder.
Builds a 21-dim vector `[age_code, gender_enc, occupation_code,
genre_value_for_each_of_18_genres]` and runs it through the **same**
StandardScaler the cold-start model was trained with. The vector then goes
into `kmeans.predict()`.

### `errors.py`

Three custom exceptions (`UserNotFoundError`, `InferenceError`,
`ServiceStartingError`) and `register_exception_handlers(app)` which wires
each to its HTTP status code + JSON shape. Also handles
`RequestValidationError` (raised by Pydantic on bad input) and reformats
its errors into our documented `details.field_errors[]` shape.

The pattern is: **business code raises a Python exception, the handler
turns it into an `ErrorResponse`**. The endpoint code is therefore free of
HTTP plumbing — it just raises `UserNotFoundError("999")` and trusts the
handler to produce a 404.

### `self_test.py`

`run_startup_self_test(state)` runs one warm and one cold inference at
boot and asserts shape invariants (5 results, descending scores, none
already rated). Lives separately because it's important enough to be
explicit. Failure raises `RuntimeError` and the lifespan propagates it.

### `api/recommend.py`

The `POST /recommendations` endpoint. Reads ~50 lines and is mostly
orchestration:

1. Get `state` via `Depends(_get_state)`.
2. Call `decide_path(payload, state)`.
3. Branch on `decision.kind`:
   - `"warm"` → `recommend_warm(...)` → build `RecommendationResponse`.
   - `"cold_stored"` → `recommend_cold_for_known_user(...)`.
   - `"cold_request"` → `recommend_cold_with_profile(...)`.
4. Wrap any exception from inference in `InferenceError` so it surfaces as
   500.

Notice there is no try/except for "expected" errors: validation is handled
upstream by Pydantic, "user not found" raises `UserNotFoundError` deep in
`routing.py`. The endpoint code reads almost like pseudocode.

### `api/health.py`

`GET /health` — reads `request.app.state.app_state` and reports counts +
loaded flags. Returns a `"starting"` snapshot if `app_state` is missing
(rare; lifespan is awaited before serving). Pure read of in-memory state;
no I/O.

### `api/reference.py`

`GET /reference-data` — wraps `constants.GENRE_NAMES`, `AGE_MAP`,
`OCCUPATION_MAP`, `GENDERS` in the documented response shape. The frontend
calls this once at startup to render dropdowns; the response is constant
for the process's lifetime.

### `inference/warm.py`

`recommend_warm(state, user_id_int, count)`. Loops over every item the
user has not rated, calls `state.svd_model.predict(uid_str, item_str)` for
each (Surprise's API is string-keyed), sorts by `pred.est` descending,
takes top-N, builds `MovieRecommendation` instances. ~30 lines.

### `inference/cold.py`

Three public functions:

- `recommend_cold_with_profile(...)` — encode profile → KMeans cluster →
  aggregate cluster's high ratings → optional genre boost → top-N.
- `recommend_cold_for_known_user(...)` — same, but the cluster comes from
  the user's row in `cold_start_model["user_features"]`. Used when a
  known user has fewer than `rating_threshold` ratings.
- `_fallback_genre_popular(...)` — used if the matched cluster is empty
  (FR-017). Just "most popular movies in your preferred genres."

---

## 9. How the test suite works

`tests/conftest.py` defines two session-scoped fixtures:

```python
@pytest.fixture(scope="session")
def app_state() -> AppState:
    return build_state(get_settings())   # heavy: loads .pkl + .dat once

@pytest.fixture(scope="session")
def client(app_state) -> TestClient:
    app = create_app()
    app.state.app_state = app_state      # reuse the same prebuilt state
    with TestClient(app) as c:
        yield c
```

`session` scope means both fixtures run **once per pytest invocation**, not
once per test. So the 13 tests share one in-memory state (~10 s total
runtime; would be 13 × 10 s = 130 s if we used `function` scope).

`TestClient` (from FastAPI/Starlette) is a synchronous wrapper that drives
the app via the same ASGI machinery Uvicorn would. It runs the lifespan
handler too — but since we already stashed `app_state`, the test fixture's
state is reused. `client.post("/recommendations", json=...)` returns a
real `httpx.Response` with `.status_code`, `.json()`, etc.

Each test file covers one slice:

- `test_recommend_warm.py` — warm path returns 5/10/etc., 404 for unknown.
- `test_recommend_cold.py` — cold path returns descending scores, 422 for
  missing profile, count-cap rejection.
- `test_validation.py` — every malformed-profile field is named in
  `field_errors`.
- `test_health.py` — `/health` reports loaded models + non-zero counts.
- `test_reference.py` — `/reference-data` matches the constants.

Run them with `cd backend && PYTHONPATH=src ./venv/bin/python -m pytest -v`
(or the env-var-set form from the README).

---

## 10. Common modifications: where do I change X?

| Change | File(s) to edit |
|---|---|
| Add a new field to the request | `schemas.py` (add to `RecommendationRequest` or `ColdStartProfile`) |
| Add a new field to the response | `schemas.py` (`MovieRecommendation` / `RecommendationResponse`) — and populate it in `api/recommend.py` |
| Change the warm-vs-cold threshold default | `config.py` (`rating_threshold`) — env var override always works |
| Tighten input validation (e.g. ban a genre) | `schemas.py` (`@field_validator` on the relevant field) |
| Add a new endpoint | New file under `api/`; create an `APIRouter`; mount it in `main.create_app()` |
| Add a new error type | `errors.py` (new exception class + new handler) |
| Add a startup invariant check | `self_test.py` (extend `run_startup_self_test`) |
| Change the SVD candidate-filtering logic | `inference/warm.py` |
| Change the cold-start aggregation rule | `inference/cold.py` (`_aggregate_cluster`) |
| Pin a different library version | `requirements.txt` — but **only** if you also re-pickle the models |
| Add a new env-var setting | `config.py` (add a `Field` with `RECSYS_API_*` derived name) |
| Change the CORS policy | `main.create_app()` (`add_middleware(CORSMiddleware, ...)`) |

Rule of thumb: if it's a wire-format change, edit `schemas.py`; if it's a
behaviour change, edit the relevant `inference/` or `routing.py`; if it's
operational, edit `config.py` or `main.py`.

---

## 11. Glossary of FastAPI / Python concepts used here

**ASGI** — Asynchronous Server Gateway Interface. The protocol Uvicorn
speaks to FastAPI. You don't interact with it directly.

**Uvicorn** — The ASGI server. `uvicorn recsys_api.main:app` starts a
worker that listens on a port and forwards requests to the FastAPI app.

**FastAPI app** — An instance of the `FastAPI` class. Routers are mounted
on it; middleware wraps it; the lifespan handler initialises it.

**Pydantic model** — A class that subclasses `BaseModel`. You declare
fields with type annotations (e.g. `count: int = 10`); Pydantic generates
validation, JSON serialisation, and OpenAPI schema for free.

**`Literal[...]`** — Python type hint for "exactly one of these values".
We use it for closed enums so Pydantic auto-rejects out-of-set inputs.

**`@field_validator`** — Pydantic decorator for custom field-level rules.
We use it for the `user_id` (digit-or-UUID) and `preferred_genres`
(subset of `GENRE_NAMES`) checks.

**`Depends(...)`** — FastAPI's dependency injection. The framework calls
the dependency function before your endpoint and passes the result. We
use it to get the `AppState` into every endpoint without globals.

**Lifespan** — An `@asynccontextmanager` attached to the app that runs
once at startup (before `yield`) and once at shutdown (after `yield`).

**Middleware** — Functions that wrap every request. We use one,
`CORSMiddleware`, which adds the right headers for browser cross-origin
requests.

**`APIRouter`** — A grouping of related endpoints. We have three (one per
top-level path: `/recommendations`, `/health`, `/reference-data`); each
lives in its own file under `api/`. They get mounted on the app via
`app.include_router(...)` in `main.create_app()`.

**Exception handler** — A function decorated with
`@app.exception_handler(SomeError)`. When that exception bubbles up out of
an endpoint, FastAPI calls the handler instead of the endpoint and returns
its result. We use this to map our domain exceptions to JSON error
responses.

**TestClient** — A synchronous client that drives the FastAPI app
in-process (no real network). Lets pytest exercise the full HTTP stack
including validation, routing, and serialisation.

**`pickle.load`** — Python's stdlib serialiser. The two model files were
created with `pickle.dump` in the source recsys repo, and we round-trip
them here. The version pins in `requirements.txt` exist exactly because
pickle is sensitive to the importing-module's class hierarchy.

---

## Where to read more

- **FastAPI tutorial:** <https://fastapi.tiangolo.com/tutorial/> — the
  official docs are excellent and short. Start with "First Steps" and
  "Path Parameters" if anything in this walkthrough was unclear.
- **Pydantic v2 docs:** <https://docs.pydantic.dev/> — especially the
  "Models" and "Validators" sections.
- **Project documents in this repo:**
  - `../README.md` — installation & operation.
  - `docs/user-manual.md` — request/response reference.
  - `docs/quality-and-risk.md` — known limitations of the deployed models.
  - `../../specs/001-movie-recsys-api/spec.md` — feature specification
    (what we built and why).
  - `../../specs/001-movie-recsys-api/plan.md` — implementation plan
    (technical context, constitution check).
  - `../../specs/001-movie-recsys-api/data-model.md` — entity contracts
    (the canonical description of `AppState` and the wire shapes).
  - `../../specs/001-movie-recsys-api/research.md` — the 12 design
    decisions (D-01 to D-12) and their rationale.
  - `../../specs/001-movie-recsys-api/contracts/openapi.yaml` — the
    machine-readable REST contract.

Suggested next step after this walkthrough: open `main.py` and
`api/recommend.py` side by side, then trace one warm cURL through the
code line by line. After that, the rest of the codebase will be obvious.

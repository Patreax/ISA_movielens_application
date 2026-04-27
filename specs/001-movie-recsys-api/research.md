# Phase 0 — Research: Movie Recommendation REST API Backend

**Feature**: 001-movie-recsys-api
**Date**: 2026-04-27
**Plan**: [plan.md](./plan.md)

This document resolves every "NEEDS CLARIFICATION" or non-obvious choice in the Technical Context of `plan.md`. Each entry is a single decision with rationale and the alternatives that were rejected. Where the answer is dictated by an existing constitution principle or by the spec, the link is named explicitly.

---

## D-01 — Pin every library that participates in unpickling

**Decision**: Pin the following dependencies to the exact versions used by the source recsys repository (`/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys`) when the `.pkl` files were produced:

| Package | Version | Reason it matters |
|---------|---------|-------------------|
| `scikit-surprise` | `1.1.4` | Defines the `surprise.SVD` class persisted in `svd_model.pkl`. Mismatch ⇒ `AttributeError` or wrong `predict()` semantics. |
| `scikit-learn` | `1.8.0` | Defines `KMeans`, `StandardScaler`, `LabelEncoder` inside `cold_start_model.pkl`. sklearn intentionally breaks pickle compatibility across minor versions. |
| `numpy` | `1.26.4` | The source repo pins `numpy<2` (mandatory). Surprise's Cython extensions and many sklearn internals are compiled against a specific NumPy ABI. NumPy 2.x is a hard incompatibility. |
| `pandas` | `3.0.2` | The cold-start `user_features` is a DataFrame; cross-major-version unpickle of DataFrames has known edge cases (categorical dtype, index name handling). Pin to be safe. |
| `joblib` | `1.5.3` | Used internally by sklearn for parallelism markers stored in pickled estimators. |
| `scipy` | `1.17.1` | Surprise links sparse-matrix structures from scipy. |

These are read directly from `uv.lock` of the source repo and locked into `backend/requirements.txt`.

**Rationale**: Constitution Principle IV explicitly forbids the silent-failure mode "library version drift breaks unpickling". The only known mitigation is byte-exact pinning. The cost is one frozen `requirements.txt`; the benefit is that `pickle.load` either succeeds correctly or raises a clear class-resolution error at startup (caught by the self-test, FR-003).

**Alternatives considered**:

- *Re-export the models in a more portable format (joblib, ONNX, MLflow)*. Rejected: requires re-running training in the source repo, then maintaining a converter. Outside the scope of this assignment (Constitution Principle I) and adds a moving part. The `.pkl` artefacts are the deliverable.
- *Loosen pins to `>=` ranges for "minor robustness"*. Rejected: precisely the failure mode Principle IV warns against. Loose pins on these libraries silently change behaviour.
- *Run the backend on Python 3.12 with a different scikit-learn*. Rejected: same risk, no benefit.

---

## D-02 — Web framework choice: FastAPI

**Decision**: Use **FastAPI** with the standard ASGI server **Uvicorn**. Pydantic v2 (transitively via FastAPI) provides request/response validation.

**Rationale**:

- The constitution names FastAPI as the default (Technology & Scope Constraints).
- The user explicitly asked for "python fastapi rest api application" in the planning prompt.
- FastAPI auto-generates OpenAPI docs at `/docs` (Swagger UI) and `/redoc`, satisfying FR-021 (interactive documentation) without any extra code.
- Pydantic schema validation gives precise, structured error responses (FR-016) without bespoke validators.
- Stateless dependency-injection model maps cleanly to "load once at startup, share read-only references" (FR-001, FR-002).

**Alternatives considered**:

- *Flask*. Rejected. Acceptable per the constitution but would require manual OpenAPI plumbing and manual request validation — net more code for the same demo. Picking the constitution's named default removes one decision.
- *Starlette directly*. Rejected — strictly more low-level than FastAPI for no benefit on a demo.

---

## D-03 — Loading models and dataset once at startup (FastAPI lifespan)

**Decision**: Use FastAPI's **lifespan** context manager (the modern replacement for `@app.on_event("startup")`) to:

1. Read the four file paths (movies.dat, users.dat, ratings.dat, two `.pkl` files) from settings.
2. Load the three MovieLens DataFrames eagerly with the same parsers as `project1.dataset` (semicolon-separated `::`, latin-1 encoding).
3. `pickle.load` both `.pkl` artefacts.
4. Assert the SVD object is `surprise.prediction_algorithms.matrix_factorization.SVD` and the cold-start dict has the four expected keys (`kmeans`, `scaler`, `encoders`, `user_features`); raise `RuntimeError` if not — Constitution III forbids degraded-mode startup.
5. Pre-compute a few small derived structures: per-user rating sets (for FR-014 "do not recommend rated movies"), per-user rating counts (for FR-005 threshold), title lookup table.
6. Run the self-test (D-08).
7. Hand the resulting **`AppState` dataclass** to all endpoints via FastAPI dependency injection (read-only).

A lifespan failure causes Uvicorn to exit non-zero, satisfying FR-004 and Constitution III.

**Rationale**: Single canonical place for "load everything"; impossible to forget to await it; matches FastAPI 0.100+ guidance; gives a single `RuntimeError` point that the container's exit code respects. Recommendation requests cannot start serving until lifespan completes, eliminating the FR-004 "request during startup" race.

**Alternatives considered**:

- *Lazy loading on first request*. Rejected — first user pays the latency, and a missing file isn't discovered until traffic arrives. Violates FR-004 + Constitution III.
- *Module-level globals filled at import time*. Rejected — runs at gunicorn worker fork time, which can blow up before logging is configured; harder to test; unfriendly to the ASGI lifecycle.

---

## D-04 — Asset packaging: bake the models and the MovieLens-1M files into the image

**Decision**: **Default = bake** the two `.pkl` files and the three `ml-1m` `.dat` files into the Docker image at build time, copied from the local `backend/models/` and `backend/data/ml-1m/` directories. The Dockerfile also accepts a runtime override: if the operator mounts `/app/models` and/or `/app/data/ml-1m` as a volume, the mounted files take precedence. Both modes are documented in `quickstart.md` and `backend/README.md`.

**Rationale**:

- Constitution Principle III requires `docker run` to "just work" with no manual pre-step. Baking the assets means the demo machine needs only the image — no flash drive of `.pkl` files.
- Total asset size (`ml-1m` ≈ 24 MB + two `.pkl` ≈ 50 MB) is well under any reasonable container size budget; no point optimising it out.
- The volume override exists for the development loop (swap a newly-trained `.pkl` without rebuilding) and for the rare case where the school machine has a different MovieLens variant.
- The `backend/models/` and `backend/data/ml-1m/` directories are **gitignored**: the artefacts are large/binary and live in the source recsys repo; we only commit pointers (and a one-shot copy script in the README).

**Alternatives considered**:

- *Volume-mount only, never bake*. Rejected — fragile demo: presenter forgets `-v`, container fails the self-test, panic. Loses the "single `docker run`" property.
- *Download from S3 / HuggingFace at startup*. Rejected — Constitution III requires reproducible builds without private-registry network access; also adds a startup-failure mode that has nothing to do with the recsys task.
- *Commit the `.pkl` and `ml-1m` files to git*. Rejected — pollutes the repo and the assignment grader will re-clone; provenance is documented in `backend/README.md` instead.

---

## D-05 — Routing rule: warm vs cold (single endpoint)

**Decision**: One endpoint, `POST /recommendations`, accepts a JSON body with optional fields and decides internally:

```text
def route(request, state) -> "warm" | "cold":
    uid = request.user_id
    # Try to interpret as a known integer MovieLens user
    if isinstance(uid, int) or (isinstance(uid, str) and uid.isdigit()):
        uid_int = int(uid)
        if uid_int in state.known_user_ids:
            if state.rating_counts[uid_int] >= state.config.rating_threshold:
                return "warm"
            return "cold_with_stored_demographics"
    return "cold_with_request_demographics"
```

In the third branch, the request **must** include a `profile` object; if missing, we return a `422` validation error per FR-016.

**Rationale**: Captures FR-005 / FR-006 / FR-010 / FR-011 in one place. No second endpoint, no client-side branching. The third sub-state ("cold with request demographics") is the only one where the cold-start profile is required.

**Alternatives considered**:

- *Two endpoints (`/recommendations/warm`, `/recommendations/cold`)*. Rejected — pushes the routing decision onto the frontend, which would then need to query our state to know the rating count of an existing user. Also doubles the surface area in the user manual.
- *Pure cold endpoint that always uses the cold model regardless*. Rejected — defeats Principle IV's "demonstrate both deployed models".

---

## D-06 — Cold-start path for an existing user with low rating count

**Decision**: If `user_id` is a known MovieLens integer but `rating_count < threshold`, the service uses **the user's row in `cold_start_model["user_features"]`** (which already contains the precomputed cluster after fitting, per `train_cold_start_model` in the source repo) and short-circuits the encoding step. The response indicates `path: "cold"` and `details: "used stored demographics"`.

**Rationale**:

- The cold-start model was trained on every user in the dataset; their cluster is already known. Re-encoding adds nothing.
- Avoids forcing the client to supply demographics it never had.
- Matches the assumption already locked in by `spec.md` ("Existing-user-with-low-ratings fallback").
- In MovieLens-1M this branch is never actually exercised (every user has ≥20 ratings) but the rule is explicit so behaviour does not depend on dataset choice.

**Alternatives considered**:

- *Treat every existing user as warm, ignoring the threshold*. Rejected — silently violates the user-stated routing rule; presenter cannot demonstrate the threshold knob.
- *Reject the request and ask the client for demographics*. Rejected — strictly worse UX for no reason.

---

## D-07 — Inference utilities: copy what we need from project1, do not import it

**Decision**: Re-implement the small inference helpers we need (`get_top_n_for_user`, `recommend_cold_user`, `_fallback_genre_popular`, `encode_cold_user`, the `GENRE_NAMES` / `AGE_MAP` / `OCCUPATION_MAP` constants) directly in `backend/src/recsys_api/inference.py` and `features.py`. Copy them faithfully from `project1.predict` and `project1.features`, keeping behaviour identical.

**Rationale**:

- Constitution Principle II requires all backend code under `backend/`. Importing `project1` would mean either depending on the source recsys repo as a sibling directory (fragile) or vendoring it as a Python package (ten times the dependency surface for a few helper functions).
- The helpers are short, pure, and stable. Copying is the simplest contract.
- Pickle.load does **not** require `project1` to import; the cold-start dict contains only sklearn / pandas / numpy objects, and the SVD is a `surprise` class. Verified against `project1/modeling/train.py` (`save_models` only puts plain library types into the pickle).
- The recommendation source-of-truth (the `.pkl` files) is unchanged; only inference logic is rewritten in our codebase.

**Alternatives considered**:

- *Add `isa-recsys` (the source repo's package) as a `pip install -e ../ISA_movielens_recsys` dependency*. Rejected — not reproducible (the source path is host-specific), violates Principle II.
- *Repackage `project1` as a published wheel*. Rejected — out of scope for a demo.

---

## D-08 — Startup self-test (Constitution III)

**Decision**: Implement `recsys_api.self_test.run_startup_self_test(state)` which:

1. Picks a fixed warm test user (the lowest user_id, e.g., 1) and asserts `recommend_warm(user_id=1, count=5)` returns 5 movies, all unrated by user 1, with strictly descending scores.
2. Builds a fixed cold profile (`age_code=25, gender="M", occupation_code=12, preferred_genres=["Action","Sci-Fi"]`) and asserts `recommend_cold(profile, count=5)` returns 5 movies with descending scores.
3. Logs both results at INFO level.
4. Raises `RuntimeError("self-test failed: …")` with a descriptive message on any failure; the lifespan handler propagates this and the process exits non-zero.

Self-test runs as the last step of the lifespan handler, after model loading.

**Rationale**: Directly satisfies Constitution Principle III ("MUST run a self-test on startup … failure to load or inference MUST cause the process to exit non-zero") and FR-003. Picks values that exist in MovieLens-1M (user 1 always exists; "M" / 25 / 12 / Action+Sci-Fi are valid).

**Alternatives considered**:

- *Skip the self-test, rely on `/health` to surface "not ready"*. Rejected — Constitution III is explicit; skipping it would be a violation.
- *Run the self-test in a separate process before launching Uvicorn*. Rejected — duplicates loading; lifespan model is simpler.

---

## D-09 — CORS

**Decision**: Use FastAPI's `CORSMiddleware`. Default origin from the `RECSYS_API_CORS_ORIGINS` env var; default value `*`. `allow_methods` includes `GET, POST, OPTIONS`. `allow_headers` includes `Content-Type`. `allow_credentials=False` (we have no credentials anyway).

**Rationale**: FR-022 + Constitution Principle II require CORS. `*` is acceptable for a demo with no auth and no sensitive data; the env var lets the operator tighten it for a hosted demo.

---

## D-10 — Logging

**Decision**: Use `loguru` (already in the source recsys repo's stack) for application logs. Uvicorn's access logs remain on standard logging. INFO level by default, configurable via `RECSYS_API_LOG_LEVEL`.

**Rationale**: Lightweight, no extra config, matches the source repo's conventions (Constitution V, "follow conventions present in the source recsys project"). One library, one config call in `main.py`.

---

## D-11 — Configuration source

**Decision**: A single `Settings` Pydantic model (`pydantic-settings`) reads from environment variables and provides defaults. All paths, the rating threshold, the port, the CORS origin, and the log level are env-var-tunable.

| Env var | Default | Purpose |
|---------|---------|---------|
| `RECSYS_API_HOST` | `0.0.0.0` | Uvicorn bind host |
| `RECSYS_API_PORT` | `8000` | Uvicorn bind port |
| `RECSYS_API_DATA_DIR` | `/app/data/ml-1m` | Where `movies.dat`, `users.dat`, `ratings.dat` live |
| `RECSYS_API_MODELS_DIR` | `/app/models` | Where `svd_model.pkl`, `cold_start_model.pkl` live |
| `RECSYS_API_RATING_THRESHOLD` | `5` | Routing rule threshold (FR-006) |
| `RECSYS_API_CORS_ORIGINS` | `*` | Comma-separated list or `*` (D-09) |
| `RECSYS_API_LOG_LEVEL` | `INFO` | loguru level |

**Rationale**: All defaults make `docker run -p 8000:8000 isa-movielens-backend` work with no flags. Single source of truth, no multi-file YAML.

---

## D-12 — Testing strategy

**Decision**: Use `pytest` with `httpx` + FastAPI's `TestClient`. A `conftest.py` fixture builds a one-shot `AppState` from the same `.pkl` files and `ml-1m` data the runtime uses, but only at test-session scope so the load cost is paid once. Test set:

- `test_health.py`: `/health` returns 200 with model_loaded flags after lifespan startup.
- `test_reference.py`: `/reference-data` returns the 18-genre list and the 7-bucket age map and the 21-occupation map.
- `test_recommend_warm.py`: a known user_id returns N movies, none of which are in the user's rated set.
- `test_recommend_cold.py`: a UUID + profile returns N movies with descending scores.
- `test_validation.py`: malformed profiles produce 422 with named offending fields (covers FR-016).

**Rationale**: Per Constitution V testing is encouraged but not mandatory; we add the minimal set that prevents the highest-risk silent failures (unpickle drift, schema regressions, routing bugs). Anything beyond this is out of scope for the demo.

**Alternatives considered**:

- *Hypothesis property tests on the recommendation contract*. Rejected — overkill for the demo's lifetime.
- *No tests at all*. Rejected — we already need to verify that `pickle.load` succeeds with the pinned versions; an automated check catches that without a manual `docker run` round-trip.

---

## Open issues

None. All Technical Context items have a decided answer above. Phase 1 design proceeds.

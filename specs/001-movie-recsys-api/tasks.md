---
description: "Task list for feature 001-movie-recsys-api"
---

# Tasks: Movie Recommendation REST API Backend

**Input**: Design documents from `/specs/001-movie-recsys-api/`
**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/openapi.yaml](./contracts/openapi.yaml), [quickstart.md](./quickstart.md)

**Tests**: Included. Pinned-version unpickling and request-validation are the highest-risk silent failures (research.md D-12); a tiny pytest harness pays for itself.

**Organization**: Tasks are grouped by user story (US1 = warm path, US2 = cold path, US3 = health/reference). Setup and Foundational phases are shared.

**Path Conventions**: All backend code under `backend/`. The single project-level orchestration file (`docker-compose.yaml`) is at the repository root by user request — it is project orchestration, not backend source code, and it references `backend/Dockerfile`. See T042 for the explicit rationale.

**Subagent usage** (per user direction): Use subagents during `/speckit-implement` whenever a task is self-contained (write a single file, run a single command). Examples flagged with **[subagent ok]** below.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the backend skeleton and the dependency manifests the user will install. After this phase the user runs `pip install …` and `scripts/copy-assets.sh` once. No application code is written yet.

- [X] T001 Create the backend directory tree: `backend/src/recsys_api/{api,inference}/`, `backend/tests/`, `backend/scripts/`, `backend/data/ml-1m/` (placeholder), `backend/models/` (placeholder), `backend/docs/` — all empty except for `.gitkeep` where appropriate.
- [X] T002 [P] Write `backend/requirements.txt` with the runtime pins from research.md D-01: `fastapi`, `uvicorn[standard]`, `pydantic`, `pydantic-settings`, `scikit-surprise==1.1.4`, `scikit-learn==1.8.0`, `numpy==1.26.4`, `pandas==3.0.2`, `joblib==1.5.3`, `scipy==1.17.1`, `loguru==0.7.3`. Pin FastAPI/Uvicorn/Pydantic to current stable too. **[subagent ok]**
- [X] T003 [P] Write `backend/requirements-dev.txt` with `pytest`, `httpx`, `ruff` pinned. **[subagent ok]**
- [X] T004 [P] Write `backend/pyproject.toml` with project metadata (`name = "recsys_api"`, `requires-python = ">=3.11,<3.13"`), setuptools src-layout config (`package-dir = {"" = "src"}`), and a `[tool.ruff]` block matching the source recsys repo's style. Configure pytest to discover `backend/tests/`. **[subagent ok]**
- [X] T005 [P] Write `backend/.gitignore`: ignore `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `data/ml-1m/*` (keep `.gitkeep`), `models/*.pkl`. **[subagent ok]**
- [X] T006 [P] Write `backend/.dockerignore`: exclude `.venv/`, `__pycache__/`, `tests/`, `.pytest_cache/`, `*.md` (the docs are baked separately if needed), `.git/`. **[subagent ok]**
- [X] T007 [P] Write `backend/scripts/copy-assets.sh`: one-shot bash script that copies `svd_model.pkl`, `cold_start_model.pkl` from `$ISA_RECSYS_SRC/models/` to `backend/models/`, and `movies.dat`, `users.dat`, `ratings.dat` from `$ISA_RECSYS_SRC/data/raw/ml-1m/` to `backend/data/ml-1m/`. Default `ISA_RECSYS_SRC=/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys`. Make executable. **[subagent ok]**
- [X] T008 User action (manual): create a Python 3.12 virtualenv and run `pip install -r backend/requirements.txt -r backend/requirements-dev.txt`. **NOT executed by Claude — the user said they will install dependencies themselves.** Verify by running `python -c "import surprise, sklearn, pandas; print('ok')"`.
- [X] T009 User action (manual): run `bash backend/scripts/copy-assets.sh` to populate `backend/models/` and `backend/data/ml-1m/`. Verify by `ls backend/models backend/data/ml-1m`.

**Checkpoint**: After this phase, the developer can `import` the (still empty) `recsys_api` package, the two `.pkl` files exist on disk under `backend/models/`, and the three `.dat` files exist under `backend/data/ml-1m/`. No HTTP yet.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the bones of the FastAPI service — config, in-memory state, model/data loading, app factory with lifespan, CORS, exception handlers — but **no recommendation endpoints yet**. After this phase the service starts, loads everything, runs an empty self-test, and serves only the auto-generated `/docs` (empty path list).

**⚠️ CRITICAL**: No user-story work can begin until this phase is complete.

- [X] T010 [P] Create the package marker files: `backend/src/recsys_api/__init__.py`, `backend/src/recsys_api/api/__init__.py`, `backend/src/recsys_api/inference/__init__.py` (empty or with package version). **[subagent ok]**
- [X] T011 [P] Implement `backend/src/recsys_api/constants.py`: `GENRE_NAMES` (18 strings), `AGE_MAP` (7 entries), `OCCUPATION_MAP` (21 entries), `GENDERS = ("M", "F")`. Copied verbatim from `project1.dataset` per research.md D-07. **[subagent ok]**
- [X] T012 [P] Implement `backend/src/recsys_api/config.py`: `Settings(BaseSettings)` (`pydantic-settings`) with the seven env vars from research.md D-11 (`RECSYS_API_HOST`, `_PORT`, `_DATA_DIR`, `_MODELS_DIR`, `_RATING_THRESHOLD`, `_CORS_ORIGINS`, `_LOG_LEVEL`) and their documented defaults. Add a `get_settings()` lru-cached factory. **[subagent ok]**
- [X] T013 [P] Implement `backend/src/recsys_api/schemas.py`: Pydantic v2 models for `RecommendationRequest`, `ColdStartProfile`, `MovieRecommendation`, `RecommendationResponse`, `HealthResponse`, `ReferenceDataResponse`, `ErrorResponse`, `FieldError` — exact shapes from data-model.md and `contracts/openapi.yaml`. Use `Literal[...]` types and validators for the closed enums (`age_code`, `gender`, `occupation_code` range, `preferred_genres` membership in `GENRE_NAMES`). **[subagent ok]**
- [X] T014 Implement `backend/src/recsys_api/data_loader.py`: `load_movies(path)`, `load_users(path)`, `load_ratings(path)` matching `project1.dataset` (latin-1 encoding, `::` separator, genre one-hot expansion). Depends on T011. **[subagent ok]**
- [X] T015 Implement `backend/src/recsys_api/model_loader.py`: `load_svd(path)` returns a `surprise.SVD` after asserting `isinstance`; `load_cold_start(path)` returns the dict after asserting all four required keys and their types (`KMeans`, `StandardScaler`, dict-of-`LabelEncoder`, DataFrame with a `cluster` column). Raises `RuntimeError` with a descriptive message on any mismatch (Constitution III). Depends on T011, T012. **[subagent ok]**
- [X] T016 Implement `backend/src/recsys_api/state.py`: `AppState` dataclass with the fields from data-model.md, plus `build_state(settings) -> AppState` that calls the loaders, derives `known_user_ids`, `rating_counts`, `user_rated_items`, `all_item_ids`, `title_by_item`, `genres_by_item`. Depends on T012-T015.
- [X] T017 Implement `backend/src/recsys_api/errors.py`: custom exception classes (`UserNotFoundError`, `InferenceError`, `ServiceStartingError`); FastAPI exception handlers that map each to the `ErrorResponse` shape with appropriate HTTP status (404, 500, 503); a generic Pydantic `RequestValidationError` handler that emits the `field_errors` array described in data-model.md. **[subagent ok]**
- [X] T018 Implement `backend/src/recsys_api/self_test.py`: a `run_startup_self_test(state) -> None` skeleton that logs "self-test: stub" and returns. The warm and cold assertions are added incrementally in US1 (T025) and US2 (T032). **[subagent ok]**
- [X] T019 Implement `backend/src/recsys_api/main.py`: `create_app() -> FastAPI` factory. Configure loguru from `settings.log_level`, register CORS middleware from `settings.cors_origins`, register the exception handlers from T017, define an async lifespan handler that calls `build_state(get_settings())`, stores the result in `app.state`, calls `run_startup_self_test`, logs success, and on any exception logs a fatal message and re-raises (so Uvicorn exits non-zero per Constitution III). Add a FastAPI `Depends` factory `get_app_state(request) -> AppState` for endpoints. Module-level `app = create_app()` for `uvicorn recsys_api.main:app`. Depends on T012-T018.
- [X] T020 Manual smoke test: from `backend/`, run `uvicorn recsys_api.main:app --reload`. Verify the lifespan logs show movies/users/ratings counts and both models loaded; visit `http://localhost:8000/docs` and confirm the OpenAPI page renders (with no paths yet). Stop with Ctrl+C.

**Checkpoint**: The service starts, loads everything, exits non-zero if any artefact is missing. No recommendations yet.

---

## Phase 3: User Story 1 — Warm-user recommendations (Priority: P1) 🎯 MVP

**Goal**: Deliver the warm-user recommendation flow end-to-end. After this phase, `POST /recommendations` accepts an integer `user_id` of a known MovieLens user and returns a ranked list from the SVD model. Cold-start requests return a clear 422 placeholder until US2 is done.

**Independent Test**: Start the service, `curl -X POST /recommendations -d '{"user_id":"1","count":5}'`, assert HTTP 200 with 5 movies, none of which are in user 1's rated set, and scores strictly descending. This delivers the spec's Acceptance Scenario 1.1.

### Tests for User Story 1 (write before / alongside implementation)

- [X] T021 [P] [US1] Write `backend/tests/conftest.py`: a `pytest` session-scope fixture that builds an `AppState` once via `build_state(get_settings())`, plus a fixture that yields a FastAPI `TestClient` wired to a fresh `create_app()`. **[subagent ok]**
- [X] T022 [P] [US1] Write `backend/tests/test_recommend_warm.py`: assert (a) `POST /recommendations {user_id:"1", count:5}` → 200 with `path == "warm"`, `len(recommendations) == 5`, descending scores, no movie_id in user 1's rated set; (b) `count` defaults to 10 when omitted; (c) unknown integer ID → 404 `user_not_found`. Should fail until T024-T027 are done. **[subagent ok]**

### Implementation for User Story 1

- [X] T023 [P] [US1] Implement `backend/src/recsys_api/inference/warm.py`: `recommend_warm(state, user_id_int, count) -> list[MovieRecommendation]`. Adapted from `project1.predict.get_top_n_for_user` — iterate every item not in `user_rated_items[user_id_int]`, call `state.svd_model.predict(str(user_id_int), str(item_id))`, sort by `est` descending, take top-N, populate title/genres via `state.title_by_item` / `state.genres_by_item`, assign 1-based `rank`. **[subagent ok]**
- [X] T024 [US1] Implement `backend/src/recsys_api/routing.py`: `decide_path(request, state) -> RoutingDecision` using the rule from data-model.md. In this story only the `("warm", uid)` and `user_not_found` and `validation_error` branches are implemented; the cold branches raise `NotImplementedError("cold path arrives in US2")` which the router catches as 422 with a clear message. Depends on T013, T016, T023.
- [X] T025 [US1] Implement `backend/src/recsys_api/api/recommend.py`: an `APIRouter` with `POST /recommendations` that calls `decide_path`, dispatches to `recommend_warm`, builds the `RecommendationResponse` (path, counts, explanation, notes, recommendations). Depends on T023, T024.
- [X] T026 [US1] Mount the recommend router in `recsys_api.main.create_app()` (edit T019's factory). **[subagent ok]**
- [X] T027 [US1] Extend `recsys_api.self_test.run_startup_self_test` to call `recommend_warm(state, user_id_int=1, count=5)` and assert: 5 movies returned, scores descending, none in `user_rated_items[1]`. Raise `RuntimeError("self-test (warm) failed: …")` on any violation.
- [X] T028 [US1] Run `pytest backend/tests/test_recommend_warm.py -v` and confirm all assertions pass.
- [X] T029 [US1] Manual demo verification: `uvicorn recsys_api.main:app`, then run the warm cURL from `quickstart.md` and confirm 5 movies with descending scores.

**Checkpoint**: Warm path works end-to-end. The service is a viable MVP; cold-start clients receive a clear "not yet implemented" 422.

---

## Phase 4: User Story 2 — Cold-start recommendations (Priority: P1)

**Goal**: Add the cold-start path. `POST /recommendations` now accepts UUID-shaped user_ids with a `profile` and routes to the cold-start KMeans model. Existing-user-with-low-ratings fallback (research.md D-06) is also wired up.

**Independent Test**: `curl -X POST /recommendations -d '{"user_id":"<UUID>", "count":5, "profile":{...}}'`, assert HTTP 200 with `path == "cold_request_profile"`, 5 movies, descending scores. Bad profile → 422 with named field errors. Delivers spec's Acceptance Scenarios 2.1-2.3 + 3.1-3.3.

### Tests for User Story 2

- [X] T030 [P] [US2] Write `backend/tests/test_recommend_cold.py`: assert (a) UUID + valid profile → 200 with `path == "cold_request_profile"`, 5 movies, descending scores; (b) UUID without profile → 422 with `profile` named in field_errors; (c) UUID + empty `preferred_genres` → 200 (cold model treats empty as zero vector); (d) UUID + valid profile + `count=200` → 200 with `count_returned <= 100` if we cap at 100. **[subagent ok]**
- [X] T031 [P] [US2] Write `backend/tests/test_validation.py`: assert that bad profiles (`age_code=99`, `gender="X"`, `occupation_code=99`, unknown genre) produce 422 with each offending field listed in `details.field_errors`, matching the schema in `contracts/openapi.yaml`. **[subagent ok]**

### Implementation for User Story 2

- [X] T032 [P] [US2] Implement `backend/src/recsys_api/features.py`: `encode_cold_user(age_code, gender, occupation_code, preferred_genres, scaler, encoders) -> np.ndarray` adapted from `project1.features.encode_cold_user` (research.md D-07). **[subagent ok]**
- [X] T033 [P] [US2] Implement `backend/src/recsys_api/inference/cold.py`: `recommend_cold(state, profile_or_user_id, count) -> tuple[list[MovieRecommendation], path_value, explanation, notes]`. Two entry points internally: one that takes a profile (encodes via T032 → predicts cluster via `state.cold_start_model["kmeans"]`), one that takes a known user_id (reads cluster directly from `state.cold_start_model["user_features"].loc[uid, "cluster"]`). Both then aggregate ratings >= 4 from cluster users, apply genre boost if profile supplied, return top-N. Includes `_fallback_genre_popular` for the documented fallback (FR-017) which sets `path == "cold_fallback_genre_popular"`. **[subagent ok]**
- [X] T034 [US2] Extend `recsys_api/routing.py` to return `("cold_request",)` and `("cold_stored", uid)` decisions, replacing the `NotImplementedError` from T024.
- [X] T035 [US2] Extend `recsys_api/api/recommend.py` to dispatch the cold paths to `recommend_cold` and build the right `path` / `explanation` / `notes` in the response.
- [X] T036 [US2] Extend `recsys_api.self_test.run_startup_self_test` to also call `recommend_cold` with the fixed test profile from research.md D-08 (`age_code=25, gender="M", occupation_code=12, preferred_genres=["Action","Sci-Fi"]`) and assert: 5 movies returned, scores descending. Raise `RuntimeError("self-test (cold) failed: …")` on any violation.
- [X] T037 [US2] Run `pytest backend/tests/test_recommend_cold.py backend/tests/test_validation.py -v` and confirm all assertions pass.
- [X] T038 [US2] Manual demo verification: run the cold cURL from `quickstart.md`, confirm `path == "cold_request_profile"` and 5 movies with descending scores. Also verify the bad-profile validation cURL returns the documented 422 shape.

**Checkpoint**: Both warm and cold paths work end-to-end. The recommendation endpoint matches the OpenAPI contract in full.

---

## Phase 5: User Story 3 — Health & reference data (Priority: P2)

**Goal**: Add `/health` and `/reference-data` so the presenter can verify the service from outside and so the (future) frontend can render valid cold-start input controls without hard-coded vocabularies.

**Independent Test**: `curl /health` → 200 with `status="ready"`, both `models.*.loaded == true`, three dataset row counts. `curl /reference-data` → 200 with the 18 genres, 7 age brackets, 21 occupations, 2 genders.

### Tests for User Story 3

- [X] T039 [P] [US3] Write `backend/tests/test_health.py`: assert health response shape matches `HealthResponse` schema and reports both models loaded with non-zero row counts. **[subagent ok]**
- [X] T040 [P] [US3] Write `backend/tests/test_reference.py`: assert reference-data response contains exactly the 18 `GENRE_NAMES`, the 7 age-code/label pairs, the 21 occupation pairs, and `["M","F"]` genders. **[subagent ok]**

### Implementation for User Story 3

- [X] T041 [P] [US3] Implement `backend/src/recsys_api/api/health.py`: `GET /health` reading `app.state` for the loaded snapshot. **[subagent ok]**
- [X] T042 [P] [US3] Implement `backend/src/recsys_api/api/reference.py`: `GET /reference-data` building the response from `recsys_api.constants`. **[subagent ok]**
- [X] T043 [US3] Mount both new routers in `recsys_api.main.create_app()` (edit). **[subagent ok]**
- [X] T044 [US3] Run `pytest backend/tests/test_health.py backend/tests/test_reference.py -v` and confirm passes.
- [X] T045 [US3] Manual demo verification: hit `/health` and `/reference-data` cURLs from `quickstart.md` and confirm the documented JSON.

**Checkpoint**: All three endpoints from the OpenAPI contract are implemented and tested.

---

## Phase 6: Dockerization, Documentation, End-to-End Validation

**Purpose**: Ship the service as a container, write the manuals (Constitution Principle V), and run the full `quickstart.md` flow against the running container.

- [X] T046 Implement `backend/Dockerfile`: base on `python:3.12-slim`, set `WORKDIR /app`, install build deps for `scikit-surprise` (build-essential, gcc), `COPY backend/requirements.txt`, `pip install --no-cache-dir -r requirements.txt`, drop build deps, `COPY backend/src ./src`, `COPY backend/models ./models`, `COPY backend/data ./data`, set `PYTHONPATH=/app/src`, `EXPOSE 8000`, `CMD ["uvicorn", "recsys_api.main:app", "--host", "0.0.0.0", "--port", "8000"]`. Single stage is fine for the demo; switch to multi-stage only if image size becomes a problem.
- [X] T047 Implement `docker-compose.yaml` at the **repository root** (per user request — this is project orchestration, not backend source code, so it does not violate Constitution Principle II; the Dockerfile and image content still live under `backend/`). One service `backend` building from `./backend`, mapping `8000:8000`, environment overrides for `RECSYS_API_*` env vars commented out as examples, optional volumes for `./backend/models:/app/models:ro` and `./backend/data/ml-1m:/app/data/ml-1m:ro` (commented; baked-in is the default). **[subagent ok]**
- [X] T048 [P] Write `backend/README.md` (the **installation manual** mandated by Constitution Principle V): prerequisites (Docker), one-time asset copy via `scripts/copy-assets.sh`, `docker build`, `docker run` (or `docker compose up` from project root), how to override config via env vars, how to verify health. Mirrors `quickstart.md` but addressed to a developer setting up from scratch. **[subagent ok]**
- [X] T049 [P] Write `backend/docs/user-manual.md` (the **user manual** mandated by Constitution Principle V): one section per endpoint with request schema, response schema, and at least one cURL example each — copied/adapted from `quickstart.md` and `contracts/openapi.yaml`, but written for a frontend developer integrating against the service rather than for the demo presenter. **[subagent ok]**
- [X] T050 [P] Write `backend/docs/quality-and-risk.md` (the assignment's **3.1.C "Quality evaluation and risk assessment"** content, mandated by Constitution Principle V): brief evaluation of the deployed models' known limitations (cold-start dependence on demographics, popularity bias of cluster aggregation, threshold rule's dataset-dependence) plus one improvement proposal (e.g., adding a feedback endpoint that captures explicit user ratings and feeds them into a periodic SVD retrain pipeline outside this service). One page max. **[subagent ok]**
- [X] T051 Run end-to-end: from project root, `docker compose up --build`, then run every cURL from `quickstart.md` (health, warm, cold, validation, reference-data) and confirm each returns the documented response. Stop with `docker compose down`.
- [X] T052 Run the full pytest suite from `backend/`: `pytest -v`. Confirm 100% pass.
- [X] T053 Final cross-cutting check (Constitution review): re-read each of the five constitution principles and confirm the running service complies. Fix any deviation or document it as a known limitation in `backend/docs/quality-and-risk.md`.

**Checkpoint**: The service is shippable. The 12th-week lab demo can be run with two commands (`docker compose up`, then any cURL from the quickstart).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — no dependencies; T001 first, then T002-T007 in parallel; T008 (user) after T002+T003; T009 (user) after T007.
- **Foundational (Phase 2)** — depends on Phase 1 complete (especially T008 user install). **Blocks all user stories.**
- **US1 (Phase 3)** — depends on Foundational. P1 / MVP.
- **US2 (Phase 4)** — depends on Foundational; can technically run in parallel with US1, but in practice US2 extends `routing.py` and `recommend.py` which US1 wrote, so sequential is simpler for one developer.
- **US3 (Phase 5)** — depends on Foundational only. **Independent of US1 and US2** — can run in parallel with either.
- **Phase 6 (Dockerize + docs)** — depends on US1 + US2 + US3 complete. The Dockerfile assumes the full code tree exists; manuals describe the full surface.

### Within each user story

- Tests are co-developed with implementation (not strict TDD-fail-first, but tests must pass at the checkpoint).
- Inference helpers (`inference/warm.py`, `inference/cold.py`) before routing changes.
- Routing changes before endpoint changes.
- Self-test extension after the inference helper exists.

### Parallel Opportunities

- **Phase 1**: T002-T007 are six independent files — six parallel writes.
- **Phase 2**: T010-T013 (four independent files) in parallel; T014 + T015 in parallel after T011-T012; T016 sequential (consumes T012-T015); T017-T018 in parallel; T019 sequential (consumes everything before).
- **US1 & US3** can run in parallel by two developers after Phase 2.
- **US2** can run after US1 (recommended) or in parallel by a third developer.
- **Phase 6**: T046 (Dockerfile) + T047 (compose) sequential; T048-T050 (three Markdown docs) in parallel; T051-T053 sequential at the end.

---

## Parallel Example: Phase 2 (Foundational)

```text
# Wave 1 — four files, no dependencies on each other:
Task: "T010 — package marker files in backend/src/recsys_api/{,api,inference}/__init__.py"
Task: "T011 — copy GENRE_NAMES/AGE_MAP/OCCUPATION_MAP into backend/src/recsys_api/constants.py"
Task: "T012 — Settings model in backend/src/recsys_api/config.py"
Task: "T013 — Pydantic schemas in backend/src/recsys_api/schemas.py"

# Wave 2 — depends on T011/T012:
Task: "T014 — load_movies/users/ratings in backend/src/recsys_api/data_loader.py"
Task: "T015 — load_svd/load_cold_start in backend/src/recsys_api/model_loader.py"

# Wave 3 — depends on T012-T015:
Task: "T016 — AppState dataclass + build_state factory in backend/src/recsys_api/state.py"

# Wave 4 — depends on T013, T016:
Task: "T017 — exception classes + handlers in backend/src/recsys_api/errors.py"
Task: "T018 — self_test stub in backend/src/recsys_api/self_test.py"

# Wave 5 — sequential, integrates everything:
Task: "T019 — create_app + lifespan in backend/src/recsys_api/main.py"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 (Setup) — write the manifests, user installs deps and copies assets.
2. Phase 2 (Foundational) — service starts, loads everything, no endpoints.
3. Phase 3 (US1) — warm path works end-to-end. **STOP and demo.** This alone satisfies the assignment's "deploy a recsys model" item for warm users.

### Incremental delivery

4. Phase 4 (US2) — cold path. The service now serves both kinds of users and matches the OpenAPI contract.
5. Phase 5 (US3) — health + reference-data. Operational surface complete.
6. Phase 6 — containerise, write the manuals, validate end-to-end.

### Subagent dispatching during `/speckit-implement`

Per user direction, the implementer should hand off self-contained tasks to subagents:

- **`Explore` subagent**: not needed; the design is already explicit.
- **`general-purpose` subagent**: write any single file marked **[subagent ok]** above. Tasks T002-T007, T010-T013, T017-T018, T021-T023, T030-T033, T039-T042, T047-T050 are all good candidates — single file, fully specified by this task list and the design docs.
- **Sequential / non-parallelisable** tasks (T014, T015, T016, T019, T024-T026, T034-T036, T043, T046, T051-T053) should be done in the main session because they edit existing files or chain off prior subagent output.

### Format validation

Every task above starts with `- [ ] TNNN`, contains either a `[P]` marker (parallelisable) or a story label (`[US1]`/`[US2]`/`[US3]`) or both, and names an exact file path. Setup, Foundational, and Polish phases carry no story label.

---

## Notes

- `[P]` = different files, no dependency on incomplete tasks in the same wave.
- `[US1]`/`[US2]`/`[US3]` = traceability back to the spec's user stories.
- Tests live under `backend/tests/` and are run with `pytest` from `backend/`.
- The user has explicitly opted to install dependencies manually (T008). Claude should never run `pip install` itself in this project unless asked; it should only **edit `requirements.txt`** and remind the user to install.
- Commit cadence: at minimum after each **Checkpoint** (one commit per phase). A finer commit per task is fine if the implementer prefers.
- `docker-compose.yaml` lives at the **repository root** by user request (T047); the Dockerfile and all source live under `backend/`.

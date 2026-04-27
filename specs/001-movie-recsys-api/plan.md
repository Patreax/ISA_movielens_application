# Implementation Plan: Movie Recommendation REST API Backend

**Branch**: `001-movie-recsys-api` | **Date**: 2026-04-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-movie-recsys-api/spec.md`

## Summary

Stand up a single-process FastAPI service that loads the two pretrained MovieLens models (`svd_model.pkl` for warm users, `cold_start_model.pkl` for new users) and the MovieLens-1M reference data into memory at startup, exposes a stateless recommendation endpoint plus health and reference-data endpoints, and is delivered as one Docker image. The service routes each request to warm-SVD or cold-KMeans inference based on a configurable rating-count threshold (default 5), returns a JSON list of ranked movies with metadata the frontend can render directly, and refuses to start if any model or dataset file fails to load (Constitution Principle III).

## Technical Context

**Language/Version**: Python 3.12 (matches `.python-version` of the source recsys repo where the `.pkl` artefacts were produced; `>=3.11,<3.13` is acceptable per the source `pyproject.toml`).
**Primary Dependencies**: FastAPI + Uvicorn (web framework + ASGI server); `scikit-surprise==1.1.4`, `scikit-learn==1.8.0`, `numpy==1.26.4` (numpy<2 is a hard constraint of the source repo), `pandas==3.0.2`, `joblib==1.5.3`, `scipy==1.17.1` — pinned to match the versions that produced the `.pkl` files (Constitution Principle IV); `loguru==0.7.3` for logging; `pydantic` (transitive via FastAPI) for request/response schemas.
**Storage**: None. MovieLens-1M (`movies.dat`, `users.dat`, `ratings.dat`) and the two `.pkl` artefacts are loaded into memory at startup; no database, no cache server.
**Testing**: `pytest` for a small set of unit + contract tests. Optional per Constitution; included for the silent-failure-prevention case (model unpickle, schema round-trip).
**Target Platform**: Linux container (single Docker image). Local development: any OS that can run Docker.
**Project Type**: Single web service. All code under `backend/`. No frontend in scope.
**Performance Goals**: Per-request end-to-end < 2 s on the demo machine for both warm and cold paths (SC-001/SC-002). Cold path is faster (one cluster lookup + groupby on the rating slice). Warm path predicts a score for every un-rated movie of the user; with ~3883 movies this is well under 1 s on a modern CPU using Surprise's vectorised path.
**Constraints**: Stateless API (FR-011). Service must start, load both models + dataset, pass self-test in < 60 s (SC-003). Image must be reproducible (Constitution III). No degraded-mode startup (Constitution III). No training in serve path (Constitution IV). All code under `backend/` (Constitution II).
**Scale/Scope**: MovieLens-1M: 6 040 users, 3 883 movies, 1 000 209 ratings. Memory footprint: ratings DataFrame (~15-25 MB), users (~250 KB), movies (~750 KB after genre one-hot), `cold_start_model` user_features (~1 MB), KMeans model (~30 KB), SVD model (~30-50 MB depending on n_factors). Total well under 200 MB, fits comfortably in any container.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Evaluated against `.specify/memory/constitution.md` v1.0.0:

| Principle | Gate | Status |
|-----------|------|--------|
| I. Demo-First Simplicity (NON-NEGOTIABLE) | Single REST service, no auth/rate-limit/queue/DB, no premature abstractions, env-var config | **PASS** — single FastAPI service; only env vars; no DB; routing is one `if/else` |
| II. Backend Scope Discipline | All code under `backend/`; JSON-over-HTTP only; CORS enabled; stable response field names | **PASS** — project structure rooted at `backend/`; CORS middleware enabled with `*` default origin; response schema documented in `contracts/openapi.yaml` |
| III. Dockerized & Reproducible Delivery | Single `docker build`+`docker run`; pinned deps; models+data baked or volume-mounted; startup self-test exits non-zero on failure | **PASS** — `backend/Dockerfile` produces one image; `requirements.txt` fully pinned; assets copied at build time (default) with optional volume override documented; lifespan handler runs warm + cold self-test on startup, raises and exits if it fails |
| IV. Pretrained Model Inference Only | No training in serve path; library versions pinned; honest error surface; documented model contract | **PASS** — only `pickle.load` at startup; pinned versions identical to those that produced the artefacts; HTTP 500 with descriptive payload on inference failure; cold-start dict keys (`kmeans`, `scaler`, `encoders`, `user_features`) and SVD type asserted at load time |
| V. Documentation for Reproduction | Installation + user manual + Quality Eval & Risk in repo, Markdown, in same commits as behaviour changes | **PLANNED** — `backend/README.md` (installation), `backend/docs/user-manual.md` (endpoints + cURL examples), `backend/docs/quality-and-risk.md` (3.1.C content); committed alongside the code in `/speckit-implement` |

**Initial gate**: PASS. No violations to justify; **Complexity Tracking** section is empty.

Re-check after Phase 1 design: see [§ Post-Design Constitution Check](#post-design-constitution-check) below.

## Project Structure

### Documentation (this feature)

```text
specs/001-movie-recsys-api/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── openapi.yaml     # Phase 1 output (REST contract)
├── checklists/
│   └── requirements.md  # Quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 output (created by /speckit-tasks)
```

### Source Code (repository root)

```text
backend/
├── Dockerfile
├── docker-compose.yml             # Optional convenience for the demo
├── .dockerignore
├── requirements.txt               # Fully pinned (Constitution IV)
├── pyproject.toml                 # Project metadata, ruff config
├── README.md                      # Installation manual (Principle V)
├── docs/
│   ├── user-manual.md             # Endpoints + cURL examples (Principle V)
│   └── quality-and-risk.md        # 3.1.C content: known limitations + improvement proposal
├── src/
│   └── recsys_api/
│       ├── __init__.py
│       ├── main.py                # FastAPI app, lifespan handler, CORS, router wiring
│       ├── config.py              # Settings (env vars: paths, threshold, port, CORS)
│       ├── data_loader.py         # Load MovieLens .dat files into pandas DataFrames
│       ├── model_loader.py        # pickle.load both .pkl, validate shape, hold AppState
│       ├── routing.py             # Decide warm vs cold from request + state
│       ├── inference.py           # warm + cold inference (adapted from project1.predict)
│       ├── features.py            # encode_cold_user (adapted from project1.features)
│       ├── schemas.py             # Pydantic request/response models
│       ├── api/
│       │   ├── __init__.py
│       │   ├── recommend.py       # POST /recommendations
│       │   ├── health.py          # GET /health
│       │   └── reference.py       # GET /reference-data
│       └── self_test.py           # Startup smoke test (one warm + one cold inference)
├── tests/
│   ├── conftest.py                # FastAPI TestClient + fixtures
│   ├── test_health.py
│   ├── test_recommend_warm.py
│   ├── test_recommend_cold.py
│   ├── test_reference.py
│   └── test_validation.py
├── data/                          # Populated at build/runtime; not committed
│   └── ml-1m/
│       ├── movies.dat
│       ├── users.dat
│       └── ratings.dat
└── models/                        # Populated at build/runtime; not committed
    ├── svd_model.pkl
    └── cold_start_model.pkl
```

**Structure Decision**: Single backend project rooted at `backend/`. Source under `backend/src/recsys_api/` (a real importable package), tests under `backend/tests/`, runtime assets (data, models) under `backend/data/` and `backend/models/`. Docker context is `backend/`. No frontend directory exists or is created — Constitution Principle II.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

*No violations. The Constitution Check above passes on all five principles with no exceptions, so this section is empty by design.*

## Post-Design Constitution Check

After completing Phase 0 research and Phase 1 design (research.md, data-model.md, contracts/openapi.yaml, quickstart.md), the constitution check was re-evaluated against the same five principles:

| Principle | Phase-1 artefacts that affect this gate | Status |
|-----------|------------------------------------------|--------|
| I. Demo-First Simplicity | `contracts/openapi.yaml` defines exactly 3 endpoints (`POST /recommendations`, `GET /health`, `GET /reference-data`); no auth schemes; no pagination; no batch endpoints | **PASS** |
| II. Backend Scope Discipline | All paths in design are under `backend/`; OpenAPI uses stable JSON field names (`movie_id`, `title`, `genres`, `score`, `rank`); CORS configurable via env var | **PASS** |
| III. Dockerized & Reproducible Delivery | `quickstart.md` confirms a single `docker build` + `docker run`; `research.md` decision D-04 commits to baking assets into the image with a volume-mount override; `self_test.py` exits non-zero on failure | **PASS** |
| IV. Pretrained Model Inference Only | `research.md` decision D-01 pins all unpickle-relevant versions; `data-model.md` documents the cold-start dict contract and the SVD type assertion done at load time; no `fit()` in serve path | **PASS** |
| V. Documentation for Reproduction | `quickstart.md` is the seed of the installation manual; `contracts/openapi.yaml` is the seed of the user manual; `backend/README.md`, `backend/docs/user-manual.md`, `backend/docs/quality-and-risk.md` are tracked tasks in the upcoming `/speckit-tasks` output and will be committed alongside the code | **PASS** |

**Post-design gate**: PASS. No new violations introduced by the design phase.

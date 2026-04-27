# ISA MovieLens Recommendation API — Installation Manual

This directory contains the FastAPI service that serves movie recommendations
from two pretrained MovieLens-1M models. It is the *backend* deliverable of
the ISA assignment (3.1.B + 3.2.A + 3.2.B). See
`../specs/001-movie-recsys-api/spec.md` for the feature specification and
`../specs/001-movie-recsys-api/contracts/openapi.yaml` for the canonical REST
contract.

This document is the **installation manual** mandated by the project
constitution (`.specify/memory/constitution.md`, Principle V). For the
endpoint-level user manual see [`docs/user-manual.md`](./docs/user-manual.md).

---

## Prerequisites

- Docker 24+
- Source recsys repository checked out locally (defaults to
  `/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys`). It supplies the
  two `.pkl` model artefacts and the MovieLens-1M raw data.

No Python is required on the host — everything runs inside the container.

---

## One-time asset copy

The two pretrained models and the MovieLens-1M raw `.dat` files are not
committed to this repository (see research.md decision D-04). Copy them once
before the first build:

```bash
cd /home/ptomco/School/5-year/LS/ISA/isa-movielens-application
bash backend/scripts/copy-assets.sh
```

The script copies:

- `svd_model.pkl`, `cold_start_model.pkl` → `backend/models/`
- `movies.dat`, `users.dat`, `ratings.dat`  → `backend/data/ml-1m/`

Override the source path by exporting `ISA_RECSYS_SRC=/path/to/...` before
running the script.

---

## Build the image

From the repository root:

```bash
docker compose build
```

…or directly:

```bash
cd backend
docker build -t isa-movielens-backend .
```

Both produce an image named `isa-movielens-backend`. All Python dependencies
are pinned in `requirements.txt` to the exact versions used to produce the
`.pkl` artefacts (Constitution Principle IV — version drift on
`scikit-surprise`, `scikit-learn`, `numpy`, `pandas`, `scipy`, `joblib` is the
most common cause of silent prediction corruption; do not widen these pins).

---

## Run

```bash
docker compose up
```

…or:

```bash
docker run --rm -p 8000:8000 --name isa-recsys isa-movielens-backend
```

On startup you should see (via loguru):

1. `lifespan: starting; data_dir=/app/data/ml-1m models_dir=/app/models`
2. `Loaded N movies / M users / K ratings`
3. `Loaded SVD model from …` and `Loaded cold-start model from …`
4. `self-test (warm): user 1 → 5 recs, top score …`
5. `self-test (cold): profile age=25/M/12/Action+Sci-Fi → 5 recs, top score …`
6. `lifespan: ready` and `Uvicorn running on http://0.0.0.0:8000`

If any of those steps fails the process exits non-zero — there is no
degraded-mode startup (Constitution III). Fix the underlying issue (typically
a missing or corrupt `.pkl` / `.dat` file) and restart.

---

## Verify the service

```bash
curl -s http://localhost:8000/health | jq
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{ "user_id": "1", "count": 5 }' | jq
```

Interactive OpenAPI docs at <http://localhost:8000/docs> (Swagger UI).

---

## Configuration (env vars)

All knobs are env-var-tunable; defaults match the demo machine.

| Variable | Default | Purpose |
|---|---|---|
| `RECSYS_API_HOST` | `0.0.0.0` | Uvicorn bind host |
| `RECSYS_API_PORT` | `8000` | Uvicorn bind port |
| `RECSYS_API_DATA_DIR` | `/app/data/ml-1m` | Where `movies.dat`, `users.dat`, `ratings.dat` live |
| `RECSYS_API_MODELS_DIR` | `/app/models` | Where `svd_model.pkl`, `cold_start_model.pkl` live |
| `RECSYS_API_RATING_THRESHOLD` | `5` | Minimum ratings for a known user to use the warm path |
| `RECSYS_API_CORS_ORIGINS` | `*` | Comma-separated origin list, or `*` |
| `RECSYS_API_LOG_LEVEL` | `INFO` | loguru level |

Example:

```bash
docker run --rm -p 8000:8000 \
  -e RECSYS_API_RATING_THRESHOLD=10 \
  -e RECSYS_API_CORS_ORIGINS="http://localhost:5173" \
  isa-movielens-backend
```

---

## Override baked-in assets at runtime

By default the image bakes the `.pkl` and `.dat` files in. To swap them
without rebuilding, mount volumes:

```bash
docker run --rm -p 8000:8000 \
  -v "$PWD/backend/models:/app/models:ro" \
  -v "$PWD/backend/data/ml-1m:/app/data/ml-1m:ro" \
  isa-movielens-backend
```

The corresponding lines in `docker-compose.yaml` are commented; uncomment to
use them.

---

## Run the local test suite (developer setup)

If you want to run pytest on the host (rather than against the container),
install the dev requirements into a Python 3.12 virtualenv and point pytest
at the local assets:

```bash
python3.12 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt -r backend/requirements-dev.txt

cd backend
PYTHONPATH=src \
  RECSYS_API_DATA_DIR="$PWD/data/ml-1m" \
  RECSYS_API_MODELS_DIR="$PWD/models" \
  pytest -v
```

The conftest defaults `RECSYS_API_DATA_DIR` and `RECSYS_API_MODELS_DIR` to
the in-repo `backend/data/ml-1m` and `backend/models`, so the env vars above
are only needed if you want to point the suite at a different asset location.

---

## Stopping the service

```bash
docker compose down
# or, for `docker run`:
docker stop isa-recsys
```

`--rm` (used by the example commands above) removes the container after it
exits, so there is nothing to clean up.

---

## Where to read more

- Endpoint-by-endpoint reference (request shapes, examples): [`docs/user-manual.md`](./docs/user-manual.md)
- Quality evaluation + risk assessment (assignment 3.1.C): [`docs/quality-and-risk.md`](./docs/quality-and-risk.md)
- Feature specification + design artefacts: `../specs/001-movie-recsys-api/`
- Project constitution: `../.specify/memory/constitution.md`

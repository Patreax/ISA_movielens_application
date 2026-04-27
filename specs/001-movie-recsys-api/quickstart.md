# Quickstart — Movie Recommendation REST API Backend

**Feature**: 001-movie-recsys-api
**Audience**: Reviewer, demo presenter, frontend developer integrating against the backend.
**Status**: Phase 1 design artefact. The actual `backend/` source tree is built by `/speckit-implement`. The commands below are the contract that the implementation must satisfy.

---

## What this service does

A single-process Python service that loads two pretrained MovieLens-1M recommendation models (`svd_model.pkl` for warm users, `cold_start_model.pkl` for new users) and the MovieLens-1M reference data into memory at startup, then serves three REST endpoints:

| Method | Path | Purpose |
|---|---|---|
| `POST` | `/recommendations` | Get a ranked list of movie recommendations for a user. Routes to warm or cold model based on the user's identifier and rating count. |
| `GET`  | `/health` | Liveness + per-model + per-dataset readiness. |
| `GET`  | `/reference-data` | Vocabularies (genres, age brackets, occupation codes, genders) for cold-start input. |

OpenAPI / interactive docs are served at `/docs` (Swagger UI) and `/redoc` once the container is running.

---

## Prerequisites

- Docker 24+ installed.
- Source recsys repository checked out at `/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys` (or any path of your choice — adjust the copy commands below).

No Python on the host is required. Everything runs inside the container.

---

## One-time asset copy (from the source recsys repo)

The two pretrained models and the MovieLens-1M raw data are **not** committed to this repository (research.md D-04). Before the first build, copy them into `backend/models/` and `backend/data/ml-1m/`:

```bash
SRC=/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys
APP=/home/ptomco/School/5-year/LS/ISA/isa-movielens-application

mkdir -p "$APP/backend/models" "$APP/backend/data/ml-1m"

cp "$SRC/models/svd_model.pkl"       "$APP/backend/models/"
cp "$SRC/models/cold_start_model.pkl" "$APP/backend/models/"

cp "$SRC/data/raw/ml-1m/movies.dat"  "$APP/backend/data/ml-1m/"
cp "$SRC/data/raw/ml-1m/users.dat"   "$APP/backend/data/ml-1m/"
cp "$SRC/data/raw/ml-1m/ratings.dat" "$APP/backend/data/ml-1m/"
```

`backend/.gitignore` excludes both subtrees.

---

## Build

```bash
cd backend
docker build -t isa-movielens-backend .
```

Single command, no pre-steps, fully reproducible (Constitution Principle III). All Python dependencies are pinned (research.md D-01) and installed inside the image; the assets are copied in at build time (default; volume override below).

---

## Run

```bash
docker run --rm -p 8000:8000 --name isa-recsys isa-movielens-backend
```

Watch the logs for:

1. `lifespan: loading MovieLens dataset…` followed by row counts for movies / users / ratings.
2. `lifespan: loading svd_model.pkl …` and `lifespan: loading cold_start_model.pkl …`.
3. `lifespan: running self-test…` — performs one warm and one cold inference (research.md D-08).
4. `Uvicorn running on http://0.0.0.0:8000`.

If any step fails the container exits non-zero with a clear log line — there is no degraded-mode startup.

### Optional: override assets at runtime (volume mount)

```bash
docker run --rm -p 8000:8000 \
  -v "$PWD/models:/app/models:ro" \
  -v "$PWD/data/ml-1m:/app/data/ml-1m:ro" \
  isa-movielens-backend
```

Mounted files take precedence over the ones baked into the image.

### Optional: tune the routing threshold or CORS

```bash
docker run --rm -p 8000:8000 \
  -e RECSYS_API_RATING_THRESHOLD=10 \
  -e RECSYS_API_CORS_ORIGINS="http://localhost:5173" \
  isa-movielens-backend
```

---

## Verify the service is healthy

```bash
curl -s http://localhost:8000/health | jq
```

Expected (counts will match MovieLens-1M):

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

---

## Demo flow 1 — Warm user (existing MovieLens user)

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{ "user_id": "1", "count": 5 }' | jq
```

Expected (illustrative; exact movies depend on the trained SVD):

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
      "genres": ["Action", "Crime", "Drama"], "score": 4.77 },
    { "rank": 3, "movie_id": 50, "title": "Usual Suspects, The (1995)",
      "genres": ["Crime", "Thriller"], "score": 4.74 },
    { "rank": 4, "movie_id": 527, "title": "Schindler's List (1993)",
      "genres": ["Drama", "War"], "score": 4.72 },
    { "rank": 5, "movie_id": 912, "title": "Casablanca (1942)",
      "genres": ["Drama", "Romance", "War"], "score": 4.69 }
  ],
  "notes": []
}
```

Verify behaviour:

- All 5 movies are titles user 1 has **not** rated (FR-014).
- Scores are strictly descending.
- `path` is `"warm"`.

---

## Demo flow 2 — Cold-start user (new UUID)

```bash
UUID=$(uuidgen)
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d "$(cat <<EOF
{
  "user_id": "$UUID",
  "count": 5,
  "profile": {
    "age_code": 25,
    "gender": "M",
    "occupation_code": 12,
    "preferred_genres": ["Action", "Sci-Fi"]
  }
}
EOF
)" | jq
```

Expected (illustrative):

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
      "genres": ["Action", "Adventure", "Drama", "Sci-Fi", "War"], "score": 4.55 },
    { "rank": 2, "movie_id": 1210,
      "title": "Star Wars: Episode VI - Return of the Jedi (1983)",
      "genres": ["Action", "Adventure", "Romance", "Sci-Fi", "War"], "score": 4.50 },
    "..."
  ],
  "notes": []
}
```

Verify behaviour:

- `path` is `"cold_request_profile"`.
- The cluster id appears in `explanation` (debugging value for the demo).
- Scores are strictly descending.

---

## Validation flow — Bad cold-start profile

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

Expected (HTTP 422):

```json
{
  "error": "validation_error",
  "message": "request validation failed",
  "details": {
    "field_errors": [
      { "field": "profile.age_code",         "message": "must be one of [1,18,25,35,45,50,56]" },
      { "field": "profile.gender",           "message": "must be one of ['M','F']" },
      { "field": "profile.occupation_code",  "message": "must be in 0..20" },
      { "field": "profile.preferred_genres[1]", "message": "unknown genre 'NotARealGenre'" }
    ]
  }
}
```

---

## Reference-data endpoint

```bash
curl -s http://localhost:8000/reference-data | jq
```

Returns the 18 genres, the 7-bracket age map, the 21-occupation map, and the gender list — exactly the values the cold-start model was trained on.

---

## Stop

```bash
docker stop isa-recsys
```

(or `Ctrl+C` in the foreground terminal — `--rm` cleans up automatically.)

---

## How this maps to the assignment

| Assignment item | Location |
|---|---|
| 3.1.B (Deployment of one RecSys model) | The two `.pkl` artefacts loaded by this service. |
| 3.1.C (Quality evaluation & risk assessment) | `backend/docs/quality-and-risk.md` (created during `/speckit-implement`). |
| 3.2.A (Docker image) | `backend/Dockerfile`; the build + run commands above. |
| 3.2.B (Installation manual + user manual) | `backend/README.md` (installation) + `backend/docs/user-manual.md` (endpoints + cURL examples). |

---

## What this Quickstart is NOT

- It is **not** the user manual. The user manual lives at `backend/docs/user-manual.md` and is written for a frontend developer, not for the demo presenter.
- It does **not** describe how to retrain the models. Retraining lives in the source recsys repo (`notebooks/01_movielens_recsys.ipynb`); this backend only serves pretrained artefacts (Constitution Principle IV).

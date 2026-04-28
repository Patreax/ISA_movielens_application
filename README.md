# ISA MovieLens Application

This is our ISA assignment project. It wraps the MovieLens-1M recommender we
trained back in **Project 1** (the
`ISA_movielens_recsys` repo — SVD for warm users, KMeans clusters for the
cold-start path) and exposes it as a small web service.

The repository is organised as a multi-package monorepo:

```
isa-movielens-application/
├── backend/          # FastAPI service that serves the pretrained models
├── frontend/         # (coming soon) React UI that talks to the backend
├── docker-compose.yaml
└── README.md         # you are here
```

The **backend** is done and dockerized. The **frontend** is the next deliverable
— it will be a React app, also dockerized, and we will add it as a second
service to `docker-compose.yaml` so that `docker compose up` brings up the
whole stack at once. Until then, only the backend service is wired up.

If you want the deeper write-up of model limitations, operational risks and
the privacy / GDPR analysis, that lives in
[quality-and-risk.md](quality-and-risk.md).

---

## What it does

- `POST /recommendations` returns a ranked list of movies for either an
  existing MovieLens user (warm path, SVD) or a brand-new user described by a
  short demographic profile (cold-start path, KMeans cluster + within-cluster
  popularity).
- `GET /health` reports liveness, model load status and dataset sizes.
- `GET /reference-data` returns the controlled vocabularies (genres, age
  codes, occupation codes, genders) so the frontend can populate dropdowns
  without hard-coding the values.

The service is **stateless**: no database, no sessions, no learning at runtime
— it just loads the pretrained `.pkl` artefacts from Project 1 at startup and
serves them.

---

## Prerequisites

- Docker 24+ (with the `docker compose` plugin)

You do **not** need Python or Node installed on the host — everything runs
inside containers.

---

## Run the deployment

From the repository root:

```bash
docker compose up --build
```

That command builds the `isa-movielens-backend` image from `backend/Dockerfile`
and starts the container as `isa-recsys`, listening on
<http://localhost:8000>. Once the frontend package lands, the same command
will additionally build and start the React container (planned port:
`5173`).

To stop everything:

```bash
docker compose down
```

If you would rather not use compose (for example to override env vars
ad-hoc), the equivalent direct commands are:

```bash
docker build -t isa-movielens-backend ./backend
docker run --rm -p 8000:8000 --name isa-recsys isa-movielens-backend
```

A successful start logs the lifespan steps (models loaded, self-test passed,
`Uvicorn running on http://0.0.0.0:8000`). If any startup step fails the
container exits non-zero on purpose — there is no half-broken mode.

---

## API docs

Once the service is up, the OpenAPI contract is published by the service
itself:

- Swagger UI: <http://localhost:8000/docs>
- ReDoc:      <http://localhost:8000/redoc>
- Raw spec:   <http://localhost:8000/openapi.json>

The canonical machine-readable contract also lives in the repo at
[`specs/001-movie-recsys-api/contracts/openapi.yaml`](specs/001-movie-recsys-api/contracts/openapi.yaml).

---

## Calling `/recommendations`

The endpoint serves both the warm and the cold-start flow — the service
decides which path to take from the request body.

**Warm user** (existing MovieLens-1M user — pass the integer id as a string):

```bash
curl -s -X POST http://localhost:8000/recommendations \
  -H 'Content-Type: application/json' \
  -d '{ "user_id": "1", "count": 5 }' | jq
```

**Cold-start user** (brand-new user — pass a UUID and a profile):

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

Each response carries a `path` field telling you which branch was used
(`warm`, `cold_request_profile`, `cold_stored_demographics`, or
`cold_fallback_genre_popular`), an `explanation` string, and a
score-descending `recommendations` array.

A quick sanity check that the service is actually up:

```bash
curl -s http://localhost:8000/health | jq
```

---

## Quality, limitations & privacy

We had to evaluate the deployment for assignment section **3.1.C** —
known model limitations, operational risks, the privacy / GDPR posture, the
ML privacy-attack surface (membership inference, model inversion, …), a PETs
fit analysis, and our improvement proposals (notably an explicit feedback
endpoint and closing the 200/404 membership-inference oracle).

That whole write-up is in
[quality-and-risk.md](quality-and-risk.md). It is
worth reading before judging the service — a couple of the design choices
(plain HTTP, `404` for unknown users, baking the `.pkl` artefacts into the
image) are intentional demo-time decisions that we explicitly call out and
discuss how to fix for a real deployment.
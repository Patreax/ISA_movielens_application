# Quality Evaluation & Risk Assessment

This document satisfies the assignment's section **3.1.C** ("Quality
evaluation and risk assessment of the deployed model") and the project
constitution's Principle V (Documentation for Reproduction). It is one page,
deliberately. Detailed offline metrics for the underlying SVD and KMeans
models live in the source recsys repository (`reports/`); this file is about
the **deployed** service's known limitations and the operational risks of
shipping it.

---

## Known limitations

### Cold-start dependence on demographics

The cold-start path predicts a user's cluster from three demographic fields
(`age_code`, `gender`, `occupation_code`) plus a "preferred genres" vector.
These are coarse signals, especially gender (binary in MovieLens-1M) and
occupation (a fixed 21-class taxonomy from 2000). Two unrelated users with
the same `(age_code, gender, occupation_code)` tuple receive identical first
recommendations until they specify different `preferred_genres`. For users
in under-represented demographic combinations the matched cluster's average
ratings have high variance — the score numbers stay valid (they are real
within-cluster averages) but the *ranking* may not generalise to that
specific user.

### Popularity bias of cluster aggregation

Cold-start scoring is `mean_rating` over a cluster's high-rating subset
(rating ≥ 4), tie-broken by rating count, with a +0.5 boost for movies in
the user's preferred genres. This favours globally popular movies that
many cluster members happened to rate; it does **not** balance for genre
diversity, era, or critical reception. The same handful of household titles
(*Shawshank*, *Star Wars*, *Pulp Fiction*) tend to surface for any cluster
with broad taste. This is acceptable for a demo but a real product would
add a diversity term or an MMR-style re-ranker.

### Threshold rule's dataset-dependence

The warm/cold split uses `rating_count >= RECSYS_API_RATING_THRESHOLD`
(default 5). On MovieLens-1M every user has at least 20 ratings, so the
`cold_stored_demographics` branch is **never** exercised in the demo. The
branch is implemented (per FR-017 and research.md D-06) so that behaviour
does not silently change if the same image is pointed at a different
MovieLens variant (`ml-100k`, `ml-25m`); but the demo presenter cannot show
that branch without raising the threshold past 20 via env var. This is
documented, not a bug.

### Score range is path-dependent

Warm scores are SVD-predicted ratings (~1.0–5.0, calibrated against held-out
MovieLens ratings). Cold scores are cluster averages of high (≥4) ratings,
naturally biased upward (mostly 3.8–5.0). The user manual flags this; the
client should treat `score` as an **opaque sortable value**, not a normalised
quality estimate. Mixing warm and cold results in a single ranking is not
supported.

### No personalisation feedback loop

The service is stateless (FR-011). It does not learn from request traffic
— every user gets the same scoring as long as the `.pkl` files are
unchanged. Bad recommendations cannot be corrected without retraining
upstream and re-baking the image.

---

## Operational risks of the deployment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Library-version drift on the unpickle side breaks `.pkl` loading silently | low (now) — high (over time, as the host distro changes) | service refuses to start; dependent frontend has nothing to render | All unpickle-relevant libraries pinned to byte-exact versions in `requirements.txt`. Loader asserts class types and dict keys at startup; failure exits the process non-zero (Constitution III). |
| Asset files (`.pkl` / `.dat`) missing or corrupt at boot | low | service exits at lifespan startup with a `RuntimeError` | The Dockerfile bakes the assets into the image; `docker run` is therefore reproducible. The optional volume override is documented and not used by default. The startup self-test (warm + cold inference) is the canary. |
| `surprise.SVD.predict` is O(M) per request × M ≈ 3 883 candidates | low at the demo's RPS, never measured at higher load | per-request latency increases past the 2 s budget under sustained load | Latency budget verified offline (~0.6 s p95 on the demo machine). For higher RPS the obvious next step is precomputing the per-user top-K once after each cold start; out of scope for this demo. |
| CORS default is `*` | low at school-presentation time | a hostile origin could call the API from a user's browser | No PII or write paths exist; the only effect is recommendations being read. The `RECSYS_API_CORS_ORIGINS` env var lets the operator tighten the policy when hosted publicly. |
| Container image carries C build toolchain | none (security-irrelevant for a demo) | larger image size | Build deps are purged after pip install (single-stage Dockerfile). Switch to multi-stage if image size becomes a concern. |
| `cold_start_model.pkl` was trained against a fixed user set | none today | a future MovieLens variant would silently mis-cluster | Loader asserts the dict keys; if a future model file uses a different schema the assert raises and the container exits cleanly. |

---

## Improvement proposal — explicit feedback ingestion

The single most valuable next step would be a **feedback endpoint** that
captures explicit user ratings and feeds them into a periodic SVD retrain
pipeline (outside this service):

```http
POST /feedback
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "movie_id": 1196,
  "rating": 5
}
```

Implementation sketch:

1. The endpoint appends the `(user_id, movie_id, rating, timestamp)` tuple
   to a write-ahead log (e.g., a single SQLite file or, in a hosted setup,
   a managed Postgres). Constitution Principle I forbids adding a database
   for the demo, so this would be a **post-demo evolution** — flagged here
   for transparency.
2. A nightly batch job (Cron, GitHub Actions, Airflow — out of scope for
   this service) reads the WAL, merges new ratings into the source recsys
   repo's `ratings.dat`, retrains the SVD and the cold-start KMeans, and
   publishes new `.pkl` artefacts.
3. The next image rebuild picks them up via `scripts/copy-assets.sh`. The
   running service has zero awareness of the retraining pipeline; it
   continues to serve whatever artefacts it was started with.

This keeps the *serving* layer simple (Constitution I), keeps training out
of the serve path (Constitution IV), and gives the cold-start path a
mechanism to gradually become a warm path for repeat users — which is the
single biggest qualitative improvement available without changing the model
family.

---

## Constitution compliance check (post-implementation)

| Principle | Status |
|---|---|
| I. Demo-First Simplicity | **PASS** — single FastAPI service, no auth, no DB, no queues, env-var config only. |
| II. Backend Scope Discipline | **PASS** — all source under `backend/`. The single repo-root `docker-compose.yaml` is project orchestration, not backend source code, by explicit user direction (tasks.md T047). |
| III. Dockerized & Reproducible Delivery | **PASS** — `docker compose up` is the only command. Lifespan loads + self-tests; failure exits non-zero. Pinned deps. |
| IV. Pretrained Model Inference Only | **PASS** — only `pickle.load` at startup; no `fit()` in serve path; library versions byte-pinned. |
| V. Documentation for Reproduction | **PASS** — `README.md` (this file's installation manual sibling), `docs/user-manual.md`, and this file are committed alongside the code. |

No deviations were introduced during implementation. No follow-up
constitutional repairs are needed.

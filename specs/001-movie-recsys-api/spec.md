# Feature Specification: Movie Recommendation REST API Backend

**Feature Branch**: `001-movie-recsys-api`
**Created**: 2026-04-27
**Status**: Draft
**Input**: User description: "We need to build a simple python fast api application for recommending users movies. ... Based on the reviews threshold (which by default could be 5) we will either reference the warm model (svd_model.pkl) or the cold user model (cold_start_model.pkl). These should be loaded into memory once and inferenced as needed. ... The rest api should return recommendations, where users can set the number of recommendations, which should be returned, and all the relevant info that the frontend might need in the future should also be returned."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Recommendations for an existing MovieLens user (warm path) (Priority: P1)

A presenter (or, in a future deployment, a frontend acting on behalf of a returning user) provides a numeric MovieLens user identifier and asks the service for movie recommendations. The service recognises the user as someone with sufficient prior rating history and returns a ranked list of movies the user has not yet rated, with predicted scores and metadata that a frontend can render directly.

**Why this priority**: This is the canonical "deploy a recsys model" demonstration described by the assignment. It is the most-watched flow in the lab presentation and exercises the larger of the two models (SVD). Without this, the demo has no story.

**Independent Test**: Pick any MovieLens user ID known to be in the dataset, call the recommendation endpoint with that ID and `count=5`, and verify the response is a list of 5 movies the user has not previously rated, each with a title, genre list, and a predicted-rating score, returned in descending score order.

**Acceptance Scenarios**:

1. **Given** the service has started and loaded both models and the MovieLens dataset, **When** a client requests recommendations for a known MovieLens user identifier with `count=10`, **Then** the response contains exactly 10 movies, each carrying movie identifier, title, genre list, and a predicted-rating score, sorted by score descending, with no movie the user has already rated.
2. **Given** the service has started and loaded both models and the MovieLens dataset, **When** a client requests recommendations for a known MovieLens user identifier without specifying `count`, **Then** the response contains exactly 10 movies (the documented default).
3. **Given** the service has started, **When** a client requests recommendations for a numeric user identifier that does not exist in the MovieLens dataset, **Then** the service responds with a clear error indicating the user was not found and no recommendations are returned.

---

### User Story 2 — Recommendations for a brand-new user (cold-start path) (Priority: P1)

A presenter (or, in a future deployment, a frontend onboarding a new visitor) supplies a freshly generated UUID together with a small profile of demographics and preferred genres. The service recognises that no rating history exists for this user and returns a ranked list of movies derived from similar users in the MovieLens population.

**Why this priority**: Cold-start handling is the second of the two models the assignment requires us to deploy and is essential to demonstrate that the system also serves first-time visitors, not only the closed MovieLens user set. It is co-equal with Story 1 in importance for grading.

**Independent Test**: Send a request with a freshly generated UUID, an age bracket, a gender, an occupation code, and 2–3 preferred genres, and verify the response contains a ranked list of movies with metadata, none of which the cold user has rated (trivially, since they have no history).

**Acceptance Scenarios**:

1. **Given** the service has started, **When** a client requests recommendations for a UUID-shaped user identifier and supplies a complete cold-start profile (age bracket, gender, occupation code, preferred genres) with `count=10`, **Then** the response contains exactly 10 movies with identifier, title, genre list, and a score, ranked descending, drawn from users similar to the supplied profile.
2. **Given** the service has started, **When** a client requests recommendations for a UUID-shaped user identifier but does not supply a cold-start profile, **Then** the service responds with a clear validation error explaining which profile fields are required.
3. **Given** the service has started, **When** a client supplies a profile that contains an unknown genre name or an out-of-range age bracket / occupation code, **Then** the service responds with a clear validation error naming the offending field and the set of accepted values.

---

### User Story 3 — Service health, catalogue, and self-description (Priority: P2)

A presenter (or an operator preparing for the demo) needs a quick way to verify that the container is alive, that both models loaded successfully, that the MovieLens data is in memory, and to obtain the small reference vocabularies (genre names, age brackets, occupation codes) the cold-start endpoint expects.

**Why this priority**: Without these, every demo failure is a black box and the presenter cannot construct a valid cold-start request without reading source code. They are not the recsys feature itself, but they are the safety net for the lab session.

**Independent Test**: Hit the health endpoint and verify it reports model-loaded status and dataset row counts; hit the reference-data endpoint and verify it returns the lists of accepted genres, age brackets, and occupation codes.

**Acceptance Scenarios**:

1. **Given** the service has started successfully, **When** a client calls the health endpoint, **Then** the response indicates the service is healthy and reports that both the warm-user model and the cold-start model are loaded and that the MovieLens user, item, and rating datasets are in memory with their row counts.
2. **Given** the service has started, **When** a client calls the reference-data endpoint, **Then** the response lists the accepted genre names, age-bracket codes with human-readable labels, and occupation codes with human-readable labels.
3. **Given** the service is configured but cannot find one of the model files at startup, **When** the container starts, **Then** the process exits with a non-zero status and a log message naming the missing artefact (no degraded-mode startup is allowed by Constitution Principle III).

---

### Edge Cases

- **Recommendation count out of range**: The client requests `count=0`, a negative number, or a number larger than the number of un-rated movies available for that user. The service returns either a validation error (for non-positive values) or as many recommendations as it can produce, never silently padding with arbitrary movies.
- **User has rated almost everything**: A warm user whose rated set is close to the catalogue size requests `count=10`. The service returns all available un-rated movies (possibly fewer than 10) and the response carries an indication that fewer than the requested number were returned.
- **Cold-start profile with empty `preferred_genres`**: The list is empty. The service still produces recommendations (clustering on demographics alone) and the response is unaffected, since the cold-start model treats the genre vector as zeros in that case.
- **Cold-start profile referencing an existing MovieLens user_id by mistake**: A client sends an integer user_id that is in the dataset but also fills in cold-start preferences. The service routes the request through the warm path (the integer ID wins) and ignores the supplied profile, with an informational note in the response so the frontend can report it.
- **Existing user with too few ratings**: In the MovieLens 1M dataset every user has at least 20 ratings, so the documented threshold of 5 is never tripped by an existing user. If, however, the in-memory rating count for a known user_id falls below the threshold, the service routes the request through the cold-start model using that user's stored demographics from the dataset (no profile required from the client).
- **Models fail to load**: A `.pkl` file is missing or its dependent library version mismatches the artefact. The container exits non-zero on startup with a clear message naming the failure.
- **Concurrent requests during model load**: A client sends a request before startup has completed. The health endpoint reports unready and the recommendation endpoints return a clear "service starting" error, never partial results from half-loaded state.

## Requirements *(mandatory)*

### Functional Requirements

#### Service lifecycle

- **FR-001**: The service MUST load the SVD warm-user model (`svd_model.pkl`) and the cold-start clustering model (`cold_start_model.pkl`) into memory exactly once at startup and reuse them for every subsequent request.
- **FR-002**: The service MUST load the MovieLens reference data (movie metadata, user demographics, rating history) into memory at startup and reuse the same data structures for every subsequent request.
- **FR-003**: On startup, the service MUST run a self-test that performs one warm-user inference and one cold-start inference using built-in fixtures and MUST exit non-zero if either fails (per Constitution Principle III).
- **FR-004**: The service MUST refuse to start, with a clear log message, if any required artefact (either model or any of the three MovieLens reference files) is missing or unreadable.

#### Recommendation routing

- **FR-005**: The service MUST classify each incoming recommendation request as warm or cold using the following rule, in order:
  1. If the supplied user identifier is a positive integer that exists in the MovieLens user set AND that user has at least the configured rating-count threshold (default 5) ratings in the loaded ratings data → **warm**.
  2. Otherwise → **cold**, in which case the request MUST include a complete cold-start profile (see FR-008) unless the user identifier is a positive integer that exists in the MovieLens user set, in which case the user's stored demographics MAY be used in lieu of a request-supplied profile.
- **FR-006**: The configured rating-count threshold MUST be tunable via a single configuration value (environment variable) and MUST default to 5.
- **FR-007**: The response MUST clearly indicate which path (warm or cold) served the request, so the frontend can render appropriate context.

#### Recommendation request inputs

- **FR-008**: A cold-start profile, when supplied, MUST contain: an age-bracket code (one of 1, 18, 25, 35, 45, 50, 56), a gender (one of "M", "F"), an occupation code (integer 0–20), and a list of preferred genres (each value drawn from the documented MovieLens-1M genre vocabulary). The list of preferred genres MAY be empty.
- **FR-009**: The recommendation request MUST accept an optional `count` parameter (positive integer) controlling the number of movies returned; the default MUST be 10.
- **FR-010**: The recommendation request MUST accept either an integer user identifier (existing MovieLens user) or a UUID-shaped string identifier (new user). The service MUST NOT require any other identifier format.
- **FR-011**: The recommendation API MUST be stateless: every recommendation request MUST be self-contained and the service MUST NOT persist new-user profiles between requests. *(Confirms simplicity per Constitution Principle I; see Assumptions for the deferred alternative.)*

#### Recommendation response

- **FR-012**: The recommendation response MUST be JSON and MUST include, at minimum, for each recommended movie: a stable movie identifier (MovieLens MovieID), the movie title, the list of genre names, the score the model produced (predicted rating for warm, similarity-based score for cold), and the position (rank, starting at 1) in the returned list.
- **FR-013**: The response MUST include the user identifier echoed back, the path used (warm/cold), the count requested, the count actually returned, and a short human-readable explanation field suitable for the frontend (e.g., `"Recommendations from SVD model for known user 1234"` or `"Recommendations for new user, similar to cluster 17"`).
- **FR-014**: The response MUST sort recommendations strictly by descending model score and MUST not include any movie the user is already known to have rated (warm path) or movies that fall outside the cold-start model's recommendation set.
- **FR-015**: When fewer recommendations than requested are available, the service MUST return what it has and the response MUST make the discrepancy explicit (via the count-returned field). The service MUST NOT pad the list with arbitrary movies.

#### Validation and error handling

- **FR-016**: The service MUST validate every request and return a structured error response naming the offending field and the accepted set of values, for: unknown integer user IDs, malformed UUIDs, out-of-range age brackets, unknown gender codes, out-of-range occupation codes, unknown genre names, and non-positive `count` values.
- **FR-017**: The service MUST NOT silently fall back to a popular-movies list when an inference fails, except where the underlying cold-start model itself defines a fallback (the genre-popular fallback inside `recommend_cold_user`); any such fallback MUST be reported in the response so the caller knows the recommendation was not produced by the primary path (per Constitution Principle IV).

#### API surface

- **FR-018**: The service MUST expose a single recommendation endpoint that accepts both warm and cold inputs, returning a unified response shape, plus a health endpoint and a reference-data endpoint (FR-019, FR-020). Additional endpoints MUST NOT be introduced without a constitution-aligned reason.
- **FR-019**: The health endpoint MUST report whether the service is ready, whether each of the two models is loaded, and the row counts of the loaded MovieLens datasets.
- **FR-020**: The reference-data endpoint MUST list the accepted genre names, age-bracket codes with their labels, and occupation codes with their labels, so frontends can render valid cold-start profile inputs without hard-coding the vocabulary.
- **FR-021**: The service MUST publish OpenAPI / interactive documentation at a documented path so the frontend team can explore the schema without reading the source.
- **FR-022**: The service MUST permit cross-origin requests from the eventual frontend origin (CORS), since the frontend will live in a separate process per Constitution Principle II.

### Key Entities *(include if feature involves data)*

- **Recommendation request**: An identifier (integer or UUID), an optional cold-start profile (age bracket, gender, occupation, preferred genres), and an optional recommendation count.
- **Cold-start profile**: A small set of demographic and taste fields shaped exactly like the inputs the cold-start KMeans model was trained on (age bracket, gender, occupation, preferred genres).
- **Movie recommendation**: A single recommended item — movie identifier, title, genres, score, rank.
- **Recommendation response**: The list of movie recommendations together with metadata describing how it was produced (path used, requested vs returned counts, explanation, echoed user identifier).
- **Health snapshot**: The readiness state of the service plus per-model and per-dataset counters.
- **Reference-data snapshot**: The vocabularies (genres, age brackets, occupations) the cold-start endpoint accepts.
- **MovieLens reference data (in-memory)**: The static set of movies, users, and ratings drawn from the MovieLens-1M files (`movies.dat`, `users.dat`, `ratings.dat`), loaded once at startup.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A presenter can obtain recommendations for a known MovieLens user in under 2 seconds end-to-end from a single request issued on the demo machine.
- **SC-002**: A presenter can obtain recommendations for a freshly generated cold-start user (UUID + demographics + 3 preferred genres) in under 2 seconds end-to-end from a single request.
- **SC-003**: The service starts, loads both models, loads the MovieLens dataset, and passes its self-test in under 60 seconds on the demo machine.
- **SC-004**: 100% of demo flows scripted in the user manual (Story 1 and Story 2 examples, plus the health and reference-data endpoints) succeed on a fresh container build using only the documented commands.
- **SC-005**: A frontend developer who has not seen the source code can construct a valid cold-start request using only the published API documentation and the reference-data endpoint, in under 5 minutes.
- **SC-006**: The presenter can demonstrate both the warm and cold paths to the lab audience in under 5 minutes during the 12th-week session.

## Assumptions

- **Stateless API**: The service does not persist new-user profiles between calls. Every request that needs a cold-start profile re-supplies it. This is the simpler of the two reasonable designs and aligns with Constitution Principle I (Demo-First Simplicity). If a future iteration needs in-memory persistence ("POST /users to register, then GET /recommendations/{uuid}"), it can be added without breaking this contract.
- **Threshold semantics**: In the MovieLens-1M dataset, every user has at least 20 ratings, so the configurable threshold of 5 ratings effectively reduces to "is the integer user_id present in the dataset?". The threshold remains tunable to keep the rule explicit and to allow swapping in a sparser dataset later.
- **Existing-user-with-low-ratings fallback**: If the rating count for a known integer user_id ever falls below the threshold, the service routes through the cold-start model using that user's stored demographics from the loaded users data, rather than failing or asking the client to re-supply demographics it never had.
- **Identifier shape**: A positive integer (with or without quotes in the JSON body) is treated as a known MovieLens user ID; any other string (notably a UUID) is treated as a new user. No other identifier shapes (email, username, etc.) are supported.
- **Single deployment artefact**: The service is delivered as one container running one process; no worker pools, no separate inference service, no model server (e.g., TorchServe) are introduced. This is the Constitution Principle I baseline.
- **Pretrained artefacts only**: The two `.pkl` files come from the source recsys repository under `/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys/models/`. They are copied (or volume-mounted) into the backend's runtime tree and are never retrained at request time (Constitution Principle IV).
- **Reference data location**: The MovieLens-1M raw files (`movies.dat`, `users.dat`, `ratings.dat`) come from `data/raw/ml-1m/` of the same source repository and are similarly copied or mounted into the backend.
- **Library-version compatibility**: The Python dependencies that participate in unpickling (`scikit-surprise`, `scikit-learn`, `numpy`, `pandas`) are pinned to the versions used by the source recsys repository when the artefacts were produced. Mismatch is the most likely silent-failure source for unpickling and is mitigated by pinning, not by runtime checks.
- **Single recommendation endpoint, dual schema**: One endpoint accepts both warm and cold input shapes and returns one unified response shape, rather than two separate endpoints. This keeps the frontend integration trivial and aligns with FR-018.
- **No authentication, no rate limiting**: Per Constitution Principle I and the user's explicit guidance, the service has no auth, no rate limiting, no API keys.
- **CORS for the eventual frontend**: Cross-origin access is allowed; the exact frontend origin will be a configuration value, defaulting to `*` for the demo.
- **The presenter is the primary user**: The "user" of this backend in the demo session is the presenter and, behind the scenes, an HTTP client (cURL / HTTPie / a small frontend). End-user UX of the recommendations themselves is the frontend team's concern.

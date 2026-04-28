# Quality Evaluation & Risk Assessment

This document covers the assignment's section **3.1.C**. The first half
evaluates the deployed model and service quality. The second half evaluates
the deployment from a privacy-assurance and data-protection perspective,
The closing section proposes how the solution could be
improved — first and foremost an explicit feedback ingestion path.

---

## 1. Known limitations of the deployed model

### 1.1 Cold-start dependence on demographics

The cold-start path predicts a user's cluster from three demographic fields
(`age_code`, `gender`, `occupation_code`) plus a "preferred genres" vector.
These are coarse signals, especially gender (binary in MovieLens-1M) and
occupation (a fixed 21-class taxonomy from 2000). Two unrelated users with
the same `(age_code, gender, occupation_code)` tuple receive identical
first recommendations until they differ on `preferred_genres`. For users
in under-represented demographic combinations the matched cluster's
average ratings have high variance — the score numbers stay valid (they
are real within-cluster averages) but the *ranking* may not generalise to
that specific user.

### 1.2 Popularity bias of cluster aggregation

Cold-start scoring is `mean_rating` over a cluster's high-rating subset
(rating ≥ 4), tie-broken by rating count, with a +0.5 boost for movies in
the user's preferred genres. This favours globally popular movies that
many cluster members happened to rate; it does **not** balance for genre
diversity, era, or critical reception. The same handful of household
titles (*Shawshank*, *Star Wars*, *Pulp Fiction*) tend to surface for any
cluster with broad taste. A real product would add a diversity term or an
MMR-style re-ranker.

### 1.3 Score range is path-dependent

Warm scores are SVD-predicted ratings (~1.0–5.0, calibrated against
held-out MovieLens ratings). Cold scores are cluster averages of high
(≥4) ratings, naturally biased upward (mostly 3.8–5.0). The client
should treat `score` as an opaque sortable value, not a normalised quality
estimate. Mixing warm and cold results in a single ranking is not
supported.

### 1.4 No personalisation feedback loop

The service is stateless. It does not learn from request traffic — every
user gets the same scoring as long as the `.pkl` files are unchanged. Bad
recommendations cannot be corrected without retraining upstream and
re-baking the image. This is also the single biggest qualitative
improvement opportunity (see §4).

---

## 2. Operational risks of the deployment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Library-version drift on the unpickle side breaks `.pkl` loading silently | low (now), high (over time) | service refuses to start | All unpickle-relevant libraries pinned to byte-exact versions in `requirements.txt`. Loader asserts class types and dict keys at startup; failure exits the process non-zero. |
| Asset files (`.pkl` / `.dat`) missing or corrupt at boot | low | service exits at startup with a `RuntimeError` | The Dockerfile bakes the assets into the image, so `docker run` is reproducible. The startup self-test (warm + cold inference) is the canary. |
| `surprise.SVD.predict` is O(M) per request × M ≈ 3 883 candidates | low at the demo's RPS, untested at higher load | per-request latency increases under sustained load | Latency budget verified offline (~0.6 s p95 on the demo machine). For higher RPS the obvious next step is precomputing the per-user top-K. |
| `pickle.load` of `.pkl` artefacts at startup | low (operator-controlled assets) | code execution if a hostile artefact is mounted | Operators are expected to bake or mount only trusted artefacts produced by the source recsys repo. Documented; not enforced cryptographically (see §4 for a signing follow-up). |
| Plain HTTP on the bound port | low at demo time | request bodies and responses are observable on the wire | The container speaks plain HTTP only — for a school demo we deliberately do not enable HTTPS. A real deployment must front the container with a TLS-terminating reverse proxy. |

---

## 3. Privacy assurance & data protection

The lecture defines **privacy** as the user's ability to control their
personal data and **security** as the protection of data from unauthorised
access, modification, or destruction. We evaluate the service against
both.

### 3.1 Data inventory and classification

The service touches four data populations. All four come from the
publicly distributed MovieLens-1M release (GroupLens, University of
Minnesota), which ships under a research licence that anonymizes the
underlying participants.

| Asset | Where it lives | What it contains | Personal-data character |
|---|---|---|---|
| `movies.dat` | baked into the image | movie ID, title, genres | not personal |
| `users.dat` | baked into the image | `user_id`, `gender`, `age_code`, `occupation_code`, `zip_code` | **pseudonymized** quasi-identifiers (the classic Sweeney triple `(gender, ZIP, DOB)` is *partially* present — DOB is replaced by a 7-bucket `age_code`, `zip_code` is 5-digit US) |
| `ratings.dat` | baked into the image | `(user_id, item_id, rating, timestamp)` rows | pseudonymized behavioural data |
| `cold_start_model['user_features']` (inside `cold_start_model.pkl`) | baked into the image | per-user row indexed by `user_id` with cluster id and engineered features | pseudonymized — *every* MovieLens user's cluster membership is a model parameter |

The HTTP surface itself is conservative:

- `POST /recommendations` accepts a `user_id` (echoed back) and an
  optional cold-start profile (`age_code`, `gender`, `occupation_code`,
  `preferred_genres`). These four fields together are quasi-identifiers,
  but they are **never persisted**. They live only in process memory for
  the duration of one request.
- `GET /health` returns aggregate counters. No row-level data.
- `GET /reference-data` returns vocabulary lists; no personal data.

The wire carries quasi-identifiers but no direct identifiers, and
**persistence is the empty set**. The privacy concern is concentrated in
(a) what the *image* carries at rest, and (b) what the *model parameters*
implicitly memorise.

### 3.2 The three states of data

| State | Posture today |
|---|---|
| **At rest** (in the image) | `users.dat` and `ratings.dat` are unencrypted plaintext inside the container filesystem. Acceptable for the public MovieLens dataset; for a private dataset the assets would have to be volume-mounted from an encrypted source. |
| **In transit** (HTTP) | Plain HTTP on `:8000`. The cold-start profile and the echoed `user_id` cross the wire in cleartext. For the demo this is intentional; production needs a TLS-terminating reverse proxy. |
| **In use** (in process memory) | DataFrames and `.pkl` model objects sit in CPython memory; no isolation, no confidential-compute primitives (no SGX, no SEV-SNP). The mitigation is operator-level: run the container on a dedicated host. |

### 3.3 Centralized-learning posture

This service is a **centralized inference service** running a model that
was itself **centrally trained**. The full training set (MovieLens-1M)
was processed in one place; the trained artefacts are then shipped as a
single image. The lecture's central-learning caveat —
*"operators have access to sensitive training data"* — applies in
principle, but the training data is a publicly redistributable benchmark,
so the residual privacy cost is bounded by the dataset's own licence
rather than by our deployment choices. Distributed alternatives
(Federated Learning, Split Learning) would be a
natural fit.

### 3.4 ML privacy-attack surface

The lecture catalogues four families of ML privacy attacks. The table
maps each one to this concrete deployment.

| Attack family | Applicability here | Residual risk |
|---|---|---|
| **Membership Inference** ("was user X in the training set?") | Directly applicable — `POST /recommendations` returns **HTTP 404** for an unknown integer ID and **HTTP 200** for a known one. This is a perfect oracle: any positive integer in `[1, 6040]` reveals MovieLens-1M membership. | High in principle, low in practice — the MovieLens-1M user set is public anyway. The same code shipped against a private user table would leak who is in the table; see §4.2 for the fix. |
| **Model Inversion** (reconstruct training inputs from model outputs) | Partially applicable — SVD predictions are known to leak per-user rating patterns under repeated querying. The cold path returns within-cluster averages, which leak the cluster's collective taste (a property of ~700 people, not one). | Low — there is no rate limiting, but the underlying ratings are public. A non-public deployment would need rate limiting or differential-privacy noise on `score`. |
| **Property Inference** (uncover sensitive properties of the training set) | Applicable by design — the cold-start `explanation` field literally states `"...similar to cluster N"`, which is a property-inference output we hand the client deliberately. | Acceptable — it is the product. A privacy-strict deployment would coarsen the explanation. |
| **Parameter / Hyperparameter Inference** (steal model weights) | The full SVD weights and KMeans cluster centroids ship inside the Docker image. Anyone who can pull the image can read the parameters straight off disk. | Acceptable for the demo; the artefacts are derivative of a public dataset. For a private model the standard mitigation is to mount the artefacts at runtime instead of baking them in (already supported). |

### 3.5 Regulatory / GDPR lens

Even though MovieLens-1M is research-licensed and the service collects no
new personal data, the four GDPR-style concerns from the lecture still
map:

- **Data collection & usage**: nothing is collected beyond what the
  caller voluntarily supplies, and nothing is persisted — the cleanest
  posture under data-minimisation (GDPR Art. 5(1)(c)).
- **Consent**: not applicable to the demo. A production deployment that
  adds the feedback endpoint proposed in §4.1 *will* trigger a consent
  obligation; that is built into the proposal.

### 3.6 PETs evaluation — what fits this service, what does not

| PET | Verdict for this service |
|---|---|
| **Data masking / generalization** | Already in the dataset upstream (`age_code` is a 7-bucket generalization of DOB; `occupation` is a 21-class generalization). Adequate. |
| **Pseudonymization** | In place — MovieLens user IDs are pseudonyms; UUIDs supplied by cold-start callers are pseudonymous by construction. |
| **Differential Privacy** | Not added now. Recommended for a follow-up — applicable both to retraining (DP-SGD on SVD, DP noise on KMeans) and to the cold-start `score` (Laplace noise) to defend against repeated-query attacks. See §4.3. |
| **Homomorphic Encryption** | Not pursued — the use case is single-tenant inference on a public dataset, not multi-party computation on private inputs, and the 100×–10 000× compute overhead would kill the latency budget. |
| **Federated Learning / Split Learning** | Conceptually a fit — every user holds their ratings on-device and only model updates leave the device. Long-term redesign; see §4.3. |
| **Trusted / Secure Execution Environments** | Not pursued — the threat model does not include an untrusted host operator. |

---

## 4. Improvement proposals

### 4.1 Explicit feedback ingestion (primary improvement)

The single most valuable next step is a **feedback endpoint** that
captures explicit user ratings and feeds them into a periodic SVD retrain
pipeline (outside this service):

```http
POST /feedback
{
  "user_id": "550e8400-e29b-41d4-a716-446655440000",
  "movie_id": 1196,
  "rating": 5,
  "consent_version": "2026-04-28"
}
```

How it would work:

1. The endpoint appends the `(pseudo_user_id, movie_id, rating, timestamp)`
   tuple to a write-ahead log (a SQLite file would be enough; a real
   deployment could use Postgres).
2. A nightly batch job (Cron / GitHub Actions / Airflow — out of scope
   for the service itself) reads the log, merges new ratings into the
   training data, retrains the SVD and the cold-start KMeans, and
   publishes new `.pkl` artefacts.
3. The next image rebuild picks them up. The running service has zero
   awareness of the retraining pipeline; it serves whatever artefacts it
   was started with.

Privacy-by-design points, motivated by §3:

- **Consent**: `consent_version` anchors the rating to a versioned
  consent text; if consent is withdrawn the next compaction drops the
  user's rows (GDPR).
- **Data minimisation**: the body carries only those four fields. No IP,
  no User-Agent, no demographics on this endpoint.
- **Differential-Privacy noise during retrain**: a small Laplace
  mechanism on per-movie averages (or DP-SGD) yields an
  ε-differentially-private model and bounds the membership / property
  inference advantage.
- **Retention cap**: raw log rows older than 90 days are deleted; the
  trained model has already absorbed the signal by then (GDPR).

This keeps the serving layer simple and the training loop offline, while
giving the cold-start path a way to gradually become a warm path for
repeat users.

### 4.2 Close the membership-inference oracle

`POST /recommendations` returns HTTP 404 for an unknown integer user ID
and HTTP 200 for a known one — a perfect membership oracle. Harmless on
the public MovieLens demo, but the same code shipped against a private
user table would leak who is in the table.

The fix is small: for unknown integer IDs, route through the cold-start
genre-popular fallback and add a `notes` entry like
`"unknown user_id; served from cold-start fallback"`. The HTTP status
becomes 200 for every well-formed request and the 200/404 distinction the
oracle relies on disappears. We would gate this behind a config flag
(`RECSYS_API_PRIVACY_MODE=strict`) so the demo can keep its current,
more debuggable responses.

---

## 5. Conclusion

The service does the recommendation job correctly and reproducibly. Its
privacy posture is good *only* because the data is public and nothing is
persisted, the same code pointed at private data would leak through the
membership-inference oracle (section 3.4) and through the model parameters baked
into the image.

The two things that matter most going forward:

1. **Feedback endpoint (section 4.1)** — the only change that meaningfully
   improves recommendation quality, and the one that forces consent,
   pseudonymization, and differential privacy to be designed in from day
   one rather than bolted on later.
2. **Closing the 200/404 oracle (section 4.2)** — a small code change that
   removes the membership-inference leak before the service is ever
   pointed at non-public data.

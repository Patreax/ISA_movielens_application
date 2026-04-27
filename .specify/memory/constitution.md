<!--
SYNC IMPACT REPORT
==================
Version change: (template / unversioned) → 1.0.0
Bump rationale: Initial ratification of project constitution from template.

Principles defined (5):
  I. Demo-First Simplicity (NON-NEGOTIABLE)
  II. Backend Scope Discipline
  III. Dockerized & Reproducible Delivery
  IV. Pretrained Model Inference Only
  V. Documentation for Reproduction

Sections defined:
  - Core Principles
  - Technology & Scope Constraints
  - Development Workflow & Quality Gates
  - Governance

Templates checked:
  ✅ .specify/templates/plan-template.md — Constitution Check section uses
     generic gate placeholders compatible with these principles; no edit needed.
  ✅ .specify/templates/spec-template.md — generic; no constitution-specific
     rules embedded; no edit needed.
  ✅ .specify/templates/tasks-template.md — generic ordering; aligns with
     Principle V (manuals) and Principle III (dockerization tasks); no edit
     needed.
  ✅ .specify/templates/checklist-template.md — generic; no edit needed.
  ⚠ docs/ runtime guidance — only assignment-text.md present; no quickstart yet.
     Tracked under Principle V and DEFERRED follow-up below.
  ⚠ CLAUDE.md — currently a stub pointing at "the current plan"; will be
     updated by /speckit-plan when the first plan exists. No edit needed now.

Deferred / follow-up TODOs:
  - Author backend/README.md installation + user manual once code lands
    (required by Principle V; tracked in /speckit-plan).
  - No prior ratification date existed; RATIFICATION_DATE set to today
    (2026-04-27) as the date of first adoption.
-->

# ISA MovieLens Application Backend Constitution

## Core Principles

### I. Demo-First Simplicity (NON-NEGOTIABLE)

This backend is a school demo. Every design decision MUST favor the simplest
working option that can be demonstrated end-to-end. The code and architecture
MUST be easily presentable in a single 12th-week lab session.

Rules:

- The backend MUST be a single REST API service. No microservices, no message
  queues, no service mesh.
- No rate-limiting, authentication, authorization, multi-tenancy, async job
  queues, or background workers MAY be introduced.
- No databases beyond what is strictly required to serve recommendations from
  the loaded `.pkl` models. In-memory pandas DataFrames (loaded from the
  MovieLens `.dat` files at startup) are the default; SQL or NoSQL stores MUST
  NOT be added.
- No abstraction layer (interfaces, plugin systems, dependency-injection
  frameworks) MAY be introduced "for the future." Three similar lines beat a
  premature abstraction.
- Configuration is via environment variables and committed defaults — no
  configuration servers, no feature flags.

Rationale: The assignment grants 12 points for the intelligent-system
application and 8 points for production-readiness as a *demo* (Docker image +
manuals). Anything beyond that is gold-plating and risks the deliverable.

### II. Backend Scope Discipline

All backend source code, tests, Dockerfile, dependency manifests, and
backend-specific documentation MUST live under the `backend/` directory.
Frontend concerns are explicitly out of scope.

Rules:

- No code outside `backend/` MAY be created or modified by backend feature
  work, except for repository-root files explicitly governed by Spec Kit
  (`.specify/`, `specs/`, `CLAUDE.md`, `docs/`).
- The backend MUST expose its functionality only through documented REST
  endpoints. No shared Python packages, no direct file imports, no language
  bindings to a frontend.
- The backend MUST enable CORS for the eventual frontend origin but MUST NOT
  assume any frontend implementation detail beyond "an HTTP client that
  consumes JSON."
- API responses MUST be JSON with stable field names so the frontend team can
  render them without coordination.

Rationale: The assignment scopes our work to the backend half of the demo.
Keeping a clean directory and contract boundary prevents scope creep and lets
the frontend be developed (or swapped) independently.

### III. Dockerized & Reproducible Delivery

The backend MUST be runnable end-to-end with a single `docker build` followed
by a single `docker run` (or `docker compose up`) on a clean machine that has
only Docker installed.

Rules:

- A `backend/Dockerfile` MUST be the canonical way to build the service. The
  build MUST NOT require manual pre-steps (no "first run this script"). All
  Python dependencies MUST be installed inside the image from a pinned
  manifest (`requirements.txt` or `pyproject.toml` + lock).
- The image MUST start the API with one entrypoint command and listen on a
  documented, configurable port.
- Pretrained models (`svd_model.pkl`, `cold_start_model.pkl`) and any
  reference data files (e.g. MovieLens `movies.dat`, `ratings.dat`,
  `users.dat`) required for inference MUST be made available to the running
  container by either (a) copying them into the image at build time, or (b)
  mounting them at a documented path via volume. The chosen mechanism MUST be
  documented in the installation manual and consistent across local and demo
  environments.
- The container MUST run a self-test on startup: load both `.pkl` models and
  perform one warm-user and one cold-start inference. Failure to load or
  inference MUST cause the process to exit non-zero with a clear error
  message — no degraded-mode fallbacks.
- The Docker image MUST be reproducible: re-running the build on the same
  source tree MUST produce a working image without network access to private
  registries.

Rationale: Section 3.2.A of the assignment awards 4 points for the Docker
image, and the demo presentation must "just work" on a fresh machine. A
broken or fragile container is a hard failure, not a soft one.

### IV. Pretrained Model Inference Only

The backend serves inference from pretrained `.pkl` files. It MUST NOT train,
re-train, or fine-tune models at runtime.

Rules:

- The backend code MUST NOT contain a training loop, hyperparameter search,
  or `fit()` invocation on production paths. Any training-time utilities that
  exist for evaluation purposes (Principle V, manuals) MUST live in clearly
  separated tooling and MUST NOT be invoked by the serving process.
- Models are loaded once at startup via `pickle.load`. Versions of `surprise`,
  `scikit-learn`, `numpy`, `pandas`, and any other library that participates
  in unpickling MUST be pinned to the same versions used to train the
  artifacts. Mismatch is a known cause of silent prediction corruption.
- Inference endpoints MUST surface model errors honestly. A failed inference
  returns an HTTP error with a descriptive message; it MUST NOT silently
  return an empty list, popular-fallback list, or zero-score recommendations
  unless that fallback is the documented behaviour of the underlying model
  (e.g. the cold-start model's own genre-popular fallback when no cluster
  users are found).
- The contract between the API and the model artifacts MUST be documented:
  which keys are expected inside `cold_start_model` (kmeans, scaler,
  encoders, user_features), and which Surprise object type is expected for
  the SVD model.

Rationale: The assignment (3.1.B) is about *deploying* a recsys model, not
training one. Conflating the two would balloon scope, image size, and demo
risk; pinning versions is the only known mitigation against the well-known
"my pickle works on my machine" failure mode.

### V. Documentation for Reproduction

The backend MUST ship with two written artifacts: an installation manual and
a user manual. Both MUST be kept up to date with the code in the same commit
that changes behaviour.

Rules:

- The installation manual MUST cover: prerequisites (Docker version), how to
  obtain the model and data files, the exact `docker build` and `docker run`
  (or `docker compose`) commands, expected port, and how to verify the
  service is healthy.
- The user manual MUST cover: every REST endpoint, request schema, response
  schema, at least one worked example per endpoint (cURL or HTTPie), and the
  meaning of the returned recommendation fields.
- Both manuals MUST be in the repository (Markdown, under `backend/` or
  `docs/`) — not in an external wiki, Confluence page, or chat thread.
- A short "Quality Evaluation & Risk Assessment" section MUST exist in the
  repository documentation, addressing assignment item 3.1.C: a brief
  evaluation of the deployed model's known limitations (e.g. cold-start
  reliance on demographic clustering, popularity bias) and a proposal for at
  least one improvement (e.g. user feedback loop). One page is sufficient.
- Documentation changes MUST go in the same commit as the behaviour change
  they describe. A PR that changes an endpoint without touching the user
  manual is non-compliant.

Rationale: Assignment items 3.1.C and 3.2.B together account for 8 of the 20
total points. They are graded on the artifact, not on how well the demo
runs, so they MUST exist as committed files at submission time.

## Technology & Scope Constraints

- **Language**: Python 3.11+ (matching the `.python-version` of the source
  recsys project unless deliberately upgraded with a dependency audit).
- **Web framework**: FastAPI is the default. Flask is acceptable if simpler
  for the team. Larger frameworks (Django, Tornado) are out of scope under
  Principle I.
- **ML / inference dependencies**: `scikit-surprise` (for the SVD model),
  `scikit-learn` (for KMeans + scalers + encoders), `numpy`, `pandas`,
  `loguru`. These MUST be pinned to the versions used to produce the
  `.pkl` artifacts (Principle IV).
- **Persistence**: None beyond reading the static MovieLens reference files
  (`movies.dat`, `ratings.dat`, `users.dat`) and the `.pkl` artifacts at
  startup. No database server.
- **Out of scope**: authentication, authorization, rate limiting, API
  gateways, telemetry stacks (Prometheus/Grafana/OTEL), Kubernetes manifests,
  Helm charts, CI/CD pipelines beyond what is needed to verify the Docker
  build, and any frontend code.
- **Asset provenance**: The two pretrained models originate from
  `/home/ptomco/School/5-year/LS/ISA/ISA_movielens_recsys/models/` and were
  produced by `notebooks/01_movielens_recsys.ipynb` in that source project.
  The MovieLens reference data originates from `data/raw/ml-1m/` in the same
  source project. Their copy or mount path into this repository MUST be
  documented and reproducible.

## Development Workflow & Quality Gates

- **Spec-Kit flow**: All non-trivial backend features go through
  `/speckit-specify` → `/speckit-plan` → `/speckit-tasks` → `/speckit-implement`
  in this repository. The plan's Constitution Check MUST pass before
  implementation begins.
- **Branching**: Each feature gets its own branch via `/speckit-git-feature`.
  Direct commits to `main` are restricted to documentation-only or
  constitution amendments.
- **Pre-merge checks** (manually verified by the author; no CI is required by
  this constitution):
  1. `docker build` for the backend image succeeds from a clean cache.
  2. The container starts and its startup self-test (Principle III) passes.
  3. At least one warm-user request and one cold-start request return a
     200 response with a non-empty, well-formed payload.
  4. The installation manual and user manual reflect any endpoint or
     configuration changes in the same commit.
- **Code style**: Follow the conventions already present in the source
  recsys project (`loguru` for logging, type hints on public functions,
  no broad `except:` clauses). Linting/formatting tooling is not mandated by
  this constitution but, if added, MUST run locally and not block the demo.
- **Testing discipline**: Automated tests are encouraged but not mandatory
  given the demo nature of the project. Where a test would prevent a known
  silent-failure class (e.g. a model-version-mismatch unpickle error), it
  SHOULD be added. Manual verification through the documented user-manual
  examples is the minimum quality gate before submission.

## Governance

This constitution supersedes ad-hoc decisions made during feature work.
Where a feature plan or implementation conflicts with a principle, the
principle wins until the constitution is amended.

Amendment procedure:

1. Open a branch and run `/speckit-constitution` with the proposed change.
2. The constitution file is updated, including a new Sync Impact Report and
   a version bump per the policy below.
3. Dependent templates (`plan-template.md`, `spec-template.md`,
   `tasks-template.md`, `checklist-template.md`) and runtime guidance
   (`CLAUDE.md`, `backend/README.md`, `docs/`) are updated in the same
   commit when affected.
4. Commit the change with a message of the form
   `docs: amend constitution to vX.Y.Z (<short summary>)`.

Versioning policy (semantic):

- **MAJOR**: A principle is removed, redefined incompatibly, or governance
  rules change in a way that invalidates prior plans.
- **MINOR**: A new principle or a new section is added, or an existing
  principle is materially expanded.
- **PATCH**: Wording clarifications, typo fixes, or non-semantic
  refinements.

Compliance review:

- Every `/speckit-plan` invocation MUST execute the Constitution Check
  against this file. Violations MUST be either justified explicitly in the
  plan's Complexity Tracking section or removed before implementation.
- At submission time, the author MUST re-verify all five principles against
  the final state of the `backend/` directory and the manuals. Any deviation
  MUST be either fixed or documented as a known limitation in the Quality
  Evaluation & Risk Assessment section (Principle V).

**Version**: 1.0.0 | **Ratified**: 2026-04-27 | **Last Amended**: 2026-04-27

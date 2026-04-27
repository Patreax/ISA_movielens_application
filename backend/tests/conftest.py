"""Shared pytest fixtures.

A session-scoped AppState is built once from the real .pkl + .dat assets, then
shared across tests for speed. The TestClient drives the full FastAPI stack
(lifespan reuses the same AppState via `app.state.app_state`).
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Default test asset paths point at the in-repo backend/data and backend/models.
# Allow override via env so CI can use a different layout.
_BACKEND_DIR = Path(__file__).resolve().parents[1]
os.environ.setdefault("RECSYS_API_DATA_DIR", str(_BACKEND_DIR / "data" / "ml-1m"))
os.environ.setdefault("RECSYS_API_MODELS_DIR", str(_BACKEND_DIR / "models"))

from recsys_api.config import get_settings  # noqa: E402
from recsys_api.main import create_app  # noqa: E402
from recsys_api.self_test import run_startup_self_test  # noqa: E402
from recsys_api.state import AppState, build_state  # noqa: E402


@pytest.fixture(scope="session")
def app_state() -> AppState:
    state = build_state(get_settings())
    run_startup_self_test(state)
    return state


@pytest.fixture(scope="session")
def client(app_state: AppState) -> TestClient:
    """A TestClient whose lifespan resolves to the same AppState as `app_state`."""
    app = create_app()
    app.state.app_state = app_state
    # Skip the lifespan handler so we reuse the prebuilt AppState.
    with TestClient(app) as c:
        yield c

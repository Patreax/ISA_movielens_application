"""FastAPI application factory + lifespan handler."""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from .config import Settings, get_settings
from .errors import register_exception_handlers
from .self_test import run_startup_self_test
from .state import AppState, build_state


def _configure_logging(settings: Settings) -> None:
    logger.remove()
    logger.add(sys.stderr, level=settings.log_level.upper())


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    _configure_logging(settings)
    logger.info(
        f"lifespan: starting; data_dir={settings.data_dir} models_dir={settings.models_dir}"
    )
    try:
        state = build_state(settings)
        app.state.app_state = state
        run_startup_self_test(state)
        logger.info("lifespan: ready")
    except Exception as exc:
        logger.exception(f"lifespan: fatal startup error: {exc}")
        raise
    yield
    logger.info("lifespan: shutdown")


def create_app() -> FastAPI:
    settings = get_settings()
    _configure_logging(settings)

    app = FastAPI(
        title="ISA MovieLens Recommendation API",
        version="1.0.0",
        summary=(
            "REST API serving movie recommendations from two pretrained MovieLens-1M "
            "models (warm-user SVD + cold-start KMeans). Demo backend for ISA."
        ),
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type"],
    )

    register_exception_handlers(app)

    # Routers are mounted incrementally per the implementation plan:
    # US1 mounts /recommendations, US3 mounts /health and /reference-data.
    from .api.recommend import router as recommend_router
    from .api.health import router as health_router
    from .api.reference import router as reference_router

    app.include_router(recommend_router)
    app.include_router(health_router)
    app.include_router(reference_router)

    return app


def get_app_state(request: Request) -> AppState:
    state: AppState | None = getattr(request.app.state, "app_state", None)
    if state is None:
        from .errors import ServiceStartingError

        raise ServiceStartingError("AppState not yet initialised")
    return state


app = create_app()

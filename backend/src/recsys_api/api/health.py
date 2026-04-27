"""GET /health — liveness + per-model + per-dataset readiness snapshot."""
from __future__ import annotations

from fastapi import APIRouter, Request

from ..schemas import (
    ConfigStatus,
    DatasetStatus,
    HealthResponse,
    ModelsStatus,
    ModelStatus,
)
from ..state import AppState

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def get_health(request: Request) -> HealthResponse:
    state: AppState | None = getattr(request.app.state, "app_state", None)
    if state is None:
        return HealthResponse(
            status="starting",
            models=ModelsStatus(
                svd=ModelStatus(loaded=False), cold_start=ModelStatus(loaded=False)
            ),
            dataset=DatasetStatus(movies=0, users=0, ratings=0),
            config=ConfigStatus(rating_threshold=0, data_dir="", models_dir=""),
        )
    return HealthResponse(
        status="ready",
        models=ModelsStatus(
            svd=ModelStatus(loaded=state.svd_model is not None),
            cold_start=ModelStatus(loaded=bool(state.cold_start_model)),
        ),
        dataset=DatasetStatus(
            movies=len(state.movies),
            users=len(state.users),
            ratings=len(state.ratings),
        ),
        config=ConfigStatus(
            rating_threshold=state.config.rating_threshold,
            data_dir=str(state.config.data_dir),
            models_dir=str(state.config.models_dir),
        ),
    )

"""POST /recommendations — warm + cold dispatch."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from ..errors import InferenceError, ServiceStartingError
from ..inference.cold import (
    recommend_cold_for_known_user,
    recommend_cold_with_profile,
)
from ..inference.warm import recommend_warm
from ..routing import decide_path
from ..schemas import RecommendationRequest, RecommendationResponse
from ..state import AppState

router = APIRouter(tags=["recommendations"])


def _get_state(request: Request) -> AppState:
    state: AppState | None = getattr(request.app.state, "app_state", None)
    if state is None:
        raise ServiceStartingError("AppState not yet initialised")
    return state


@router.post(
    "/recommendations",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
)
async def post_recommendations(
    payload: RecommendationRequest,
    state: AppState = Depends(_get_state),
) -> RecommendationResponse:
    decision = decide_path(payload, state)
    notes = list(decision.notes)

    if decision.kind == "warm":
        assert decision.user_id_int is not None
        try:
            recs = recommend_warm(state, decision.user_id_int, payload.count)
        except Exception as exc:  # surfaces as HTTP 500 via InferenceError handler
            raise InferenceError("svd", exc) from exc

        if len(recs) < payload.count:
            notes.append(
                f"requested {payload.count} but only {len(recs)} unrated movies "
                f"remain for user {decision.user_id_int}"
            )

        return RecommendationResponse(
            user_id=payload.user_id,
            path="warm",
            count_requested=payload.count,
            count_returned=len(recs),
            explanation=(
                f"Recommendations from SVD model for known MovieLens "
                f"user {decision.user_id_int}"
            ),
            recommendations=recs,
            notes=notes,
        )

    if decision.kind == "cold_stored":
        assert decision.user_id_int is not None
        try:
            recs, path_value, explanation, cold_notes = recommend_cold_for_known_user(
                state, decision.user_id_int, payload.count
            )
        except Exception as exc:
            raise InferenceError("cold_start", exc) from exc
        notes.extend(cold_notes)
        return RecommendationResponse(
            user_id=payload.user_id,
            path=path_value,
            count_requested=payload.count,
            count_returned=len(recs),
            explanation=explanation,
            recommendations=recs,
            notes=notes,
        )

    # decision.kind == "cold_request"
    assert payload.profile is not None
    profile = payload.profile
    try:
        recs, path_value, explanation, cold_notes = recommend_cold_with_profile(
            state,
            age_code=profile.age_code,
            gender=profile.gender,
            occupation_code=profile.occupation_code,
            preferred_genres=profile.preferred_genres,
            count=payload.count,
        )
    except Exception as exc:
        raise InferenceError("cold_start", exc) from exc
    notes.extend(cold_notes)
    return RecommendationResponse(
        user_id=payload.user_id,
        path=path_value,
        count_requested=payload.count,
        count_returned=len(recs),
        explanation=explanation,
        recommendations=recs,
        notes=notes,
    )

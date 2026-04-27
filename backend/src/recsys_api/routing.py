"""Decide warm vs cold path from request + state (data-model.md routing rule)."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from .errors import UserNotFoundError
from .schemas import RecommendationRequest
from .state import AppState

PathKind = Literal["warm", "cold_stored", "cold_request"]


@dataclass(frozen=True)
class RoutingDecision:
    kind: PathKind
    user_id_int: int | None = None
    notes: tuple[str, ...] = ()


def decide_path(req: RecommendationRequest, state: AppState) -> RoutingDecision:
    raw = req.user_id.strip()
    if raw.isdigit():
        uid_int = int(raw)
        if uid_int not in state.known_user_ids:
            raise UserNotFoundError(raw)
        notes: list[str] = []
        rating_count = state.rating_counts.get(uid_int, 0)
        if rating_count >= state.config.rating_threshold:
            if req.profile is not None:
                notes.append(
                    "profile field was supplied but ignored because user_id is "
                    "a known warm MovieLens user"
                )
            return RoutingDecision(kind="warm", user_id_int=uid_int, notes=tuple(notes))
        if req.profile is not None:
            notes.append(
                "profile field was supplied but ignored because the known user's "
                "stored demographics are used"
            )
        return RoutingDecision(
            kind="cold_stored", user_id_int=uid_int, notes=tuple(notes)
        )

    UUID(raw)  # Pydantic already validated; this asserts the invariant.
    if req.profile is None:
        from fastapi.exceptions import RequestValidationError
        from pydantic_core import PydanticCustomError, InitErrorDetails

        raise RequestValidationError(
            errors=[
                InitErrorDetails(
                    type=PydanticCustomError(
                        "missing", "profile is required for UUID user_id"
                    ),
                    loc=("body", "profile"),
                    input=None,
                )
            ]
        )
    return RoutingDecision(kind="cold_request")

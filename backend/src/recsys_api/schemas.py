"""Pydantic v2 wire schemas — request/response shapes for the REST surface.

Canonical contract: contracts/openapi.yaml. Field shapes here must stay in sync.
"""
from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .constants import AGE_MAP, GENDERS, GENRE_NAMES

AgeCode = Literal[1, 18, 25, 35, 45, 50, 56]
Gender = Literal["M", "F"]
PathValue = Literal[
    "warm",
    "cold_request_profile",
    "cold_stored_demographics",
    "cold_fallback_genre_popular",
]
ErrorCode = Literal[
    "validation_error",
    "user_not_found",
    "inference_failed",
    "service_starting",
]

_GENRE_SET = set(GENRE_NAMES)
_AGE_SET = set(AGE_MAP.keys())


class ColdStartProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_code: AgeCode = Field(
        description=f"Must be one of {sorted(_AGE_SET)}.",
    )
    gender: Gender = Field(description=f"Must be one of {list(GENDERS)}.")
    occupation_code: int = Field(ge=0, le=20, description="MovieLens-1M occupation code (0..20).")
    preferred_genres: list[str] = Field(
        default_factory=list,
        description="Subset of MovieLens-1M genres. Empty list is allowed.",
    )

    @field_validator("preferred_genres")
    @classmethod
    def _validate_genres(cls, v: list[str]) -> list[str]:
        bad = [g for g in v if g not in _GENRE_SET]
        if bad:
            raise ValueError(
                f"unknown genre(s): {bad}. Accepted values: {GENRE_NAMES}"
            )
        seen: set[str] = set()
        deduped: list[str] = []
        for g in v:
            if g not in seen:
                seen.add(g)
                deduped.append(g)
        return deduped


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(
        description=(
            "Either a positive-integer string (existing MovieLens user) or a UUID "
            "string (new user). '0' and negative-integer strings are rejected."
        ),
    )
    count: int = Field(default=10, ge=1, le=100, description="Number of recommendations.")
    profile: ColdStartProfile | None = None

    @field_validator("user_id")
    @classmethod
    def _validate_user_id(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("user_id must be a non-empty string")
        if s.isdigit():
            n = int(s)
            if n <= 0:
                raise ValueError("integer user_id must be positive")
            return s
        try:
            UUID(s)
        except (ValueError, TypeError) as exc:
            raise ValueError(
                "user_id must be a positive integer string or a UUID"
            ) from exc
        return s


class MovieRecommendation(BaseModel):
    rank: int = Field(ge=1)
    movie_id: int
    title: str
    genres: list[str]
    score: float


class RecommendationResponse(BaseModel):
    user_id: str
    path: PathValue
    count_requested: int
    count_returned: int
    explanation: str
    recommendations: list[MovieRecommendation]
    notes: list[str] = Field(default_factory=list)


class ModelStatus(BaseModel):
    loaded: bool


class ModelsStatus(BaseModel):
    svd: ModelStatus
    cold_start: ModelStatus


class DatasetStatus(BaseModel):
    movies: int
    users: int
    ratings: int


class ConfigStatus(BaseModel):
    rating_threshold: int
    data_dir: str
    models_dir: str


class HealthResponse(BaseModel):
    status: Literal["ready", "starting"]
    models: ModelsStatus
    dataset: DatasetStatus
    config: ConfigStatus


class CodeLabel(BaseModel):
    code: int
    label: str


class ReferenceDataResponse(BaseModel):
    genres: list[str]
    age_codes: list[CodeLabel]
    occupation_codes: list[CodeLabel]
    genders: list[str]


class FieldError(BaseModel):
    field: str
    message: str
    accepted: list[str] | None = None


class ErrorDetails(BaseModel):
    field_errors: list[FieldError] | None = None

    @model_validator(mode="after")
    def _drop_none(self) -> "ErrorDetails":
        return self


class ErrorResponse(BaseModel):
    error: ErrorCode
    message: str
    details: dict | None = None

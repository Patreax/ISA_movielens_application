"""GET /reference-data — vocabularies for cold-start input."""
from __future__ import annotations

from fastapi import APIRouter

from ..constants import AGE_MAP, GENDERS, GENRE_NAMES, OCCUPATION_MAP
from ..schemas import CodeLabel, ReferenceDataResponse

router = APIRouter(tags=["reference"])


@router.get("/reference-data", response_model=ReferenceDataResponse)
async def get_reference_data() -> ReferenceDataResponse:
    return ReferenceDataResponse(
        genres=list(GENRE_NAMES),
        age_codes=[CodeLabel(code=c, label=l) for c, l in AGE_MAP.items()],
        occupation_codes=[CodeLabel(code=c, label=l) for c, l in OCCUPATION_MAP.items()],
        genders=list(GENDERS),
    )

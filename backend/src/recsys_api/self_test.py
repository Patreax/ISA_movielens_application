"""Startup self-test (research.md D-08, Constitution III, FR-003).

Phase 2 stub: logs and returns. The warm and cold assertions are added
incrementally in US1 (T027) and US2 (T036).
"""
from __future__ import annotations

from loguru import logger

from .state import AppState


def run_startup_self_test(state: AppState) -> None:
    logger.info("self-test: stub (warm + cold checks added in US1/US2)")
    _self_test_warm(state)
    _self_test_cold(state)
    logger.info("self-test: passed")


def _self_test_warm(state: AppState) -> None:
    """Filled in by T027."""
    try:
        from .inference.warm import recommend_warm
    except ImportError:
        logger.debug("self-test: warm inference not yet implemented (Phase 2 stub)")
        return

    if 1 not in state.known_user_ids:
        raise RuntimeError(
            "self-test (warm) failed: user_id=1 not present in dataset (unexpected for ML-1M)"
        )
    recs = recommend_warm(state, user_id_int=1, count=5)
    if len(recs) != 5:
        raise RuntimeError(
            f"self-test (warm) failed: expected 5 recs, got {len(recs)}"
        )
    rated = state.user_rated_items.get(1, set())
    overlap = [r.movie_id for r in recs if r.movie_id in rated]
    if overlap:
        raise RuntimeError(
            f"self-test (warm) failed: returned movies user 1 has already rated: {overlap}"
        )
    scores = [r.score for r in recs]
    if not all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)):
        raise RuntimeError(
            f"self-test (warm) failed: scores not descending: {scores}"
        )
    logger.info(f"self-test (warm): user 1 → {len(recs)} recs, top score {scores[0]:.3f}")


def _self_test_cold(state: AppState) -> None:
    """Filled in by T036."""
    try:
        from .inference.cold import recommend_cold_with_profile
    except ImportError:
        logger.debug("self-test: cold inference not yet implemented (Phase 2 stub)")
        return

    recs, _path, _explanation, _notes = recommend_cold_with_profile(
        state,
        age_code=25,
        gender="M",
        occupation_code=12,
        preferred_genres=["Action", "Sci-Fi"],
        count=5,
    )
    if len(recs) != 5:
        raise RuntimeError(
            f"self-test (cold) failed: expected 5 recs, got {len(recs)}"
        )
    scores = [r.score for r in recs]
    if not all(scores[i] >= scores[i + 1] for i in range(len(scores) - 1)):
        raise RuntimeError(
            f"self-test (cold) failed: scores not descending: {scores}"
        )
    logger.info(
        f"self-test (cold): profile age=25/M/12/Action+Sci-Fi → {len(recs)} recs, "
        f"top score {scores[0]:.3f}"
    )

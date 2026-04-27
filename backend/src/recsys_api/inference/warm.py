"""Warm-user inference (SVD).

Adapted from project1.predict.get_top_n_for_user (research.md D-07).
"""
from __future__ import annotations

from ..schemas import MovieRecommendation
from ..state import AppState


def recommend_warm(
    state: AppState,
    user_id_int: int,
    count: int,
) -> list[MovieRecommendation]:
    """Return the top-`count` SVD predictions for `user_id_int`, excluding rated movies."""
    rated = state.user_rated_items.get(user_id_int, set())
    uid_str = str(user_id_int)

    scored: list[tuple[int, float]] = []
    for item_id in state.all_item_ids:
        if item_id in rated:
            continue
        pred = state.svd_model.predict(uid_str, str(item_id))
        scored.append((item_id, float(pred.est)))

    scored.sort(key=lambda x: x[1], reverse=True)
    top = scored[:count]

    return [
        MovieRecommendation(
            rank=i + 1,
            movie_id=int(item_id),
            title=state.title_by_item.get(int(item_id), f"Movie {item_id}"),
            genres=state.genres_by_item.get(int(item_id), []),
            score=score,
        )
        for i, (item_id, score) in enumerate(top)
    ]

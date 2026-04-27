"""Cold-start inference (KMeans cluster aggregation).

Adapted from project1.predict.recommend_cold_user / _fallback_genre_popular
(research.md D-07).
"""
from __future__ import annotations

from typing import Literal

import pandas as pd

from ..constants import GENRE_NAMES
from ..features import encode_cold_user
from ..schemas import MovieRecommendation
from ..state import AppState

ColdPath = Literal["cold_request_profile", "cold_stored_demographics", "cold_fallback_genre_popular"]


def _build_recs_from_movie_scores(
    state: AppState, movie_scores: pd.DataFrame, count: int
) -> list[MovieRecommendation]:
    top = movie_scores.head(count)
    out: list[MovieRecommendation] = []
    for i, (item_id, row) in enumerate(top.iterrows()):
        iid = int(item_id)
        out.append(
            MovieRecommendation(
                rank=i + 1,
                movie_id=iid,
                title=state.title_by_item.get(iid, f"Movie {iid}"),
                genres=state.genres_by_item.get(iid, []),
                score=float(row["avg_rating"]),
            )
        )
    return out


def _aggregate_cluster(
    state: AppState,
    cluster_users: list[int],
    preferred_genres: list[str] | None,
) -> pd.DataFrame:
    cluster_ratings = state.ratings[state.ratings["user_id"].isin(cluster_users)]
    high_ratings = cluster_ratings[cluster_ratings["rating"] >= 4]
    if high_ratings.empty:
        high_ratings = cluster_ratings

    movie_scores = high_ratings.groupby("item_id").agg(
        avg_rating=("rating", "mean"),
        count=("rating", "count"),
    )

    if preferred_genres:
        genre_mask = state.movies[preferred_genres].max(axis=1) == 1
        genre_items = set(state.movies[genre_mask]["item_id"].astype(int))
        in_genre = movie_scores.index.isin(genre_items)
        movie_scores.loc[in_genre, "avg_rating"] += 0.5

    return movie_scores.sort_values(
        ["avg_rating", "count"], ascending=[False, False]
    )


def _fallback_genre_popular(
    state: AppState, preferred_genres: list[str], count: int
) -> list[MovieRecommendation]:
    if preferred_genres:
        genre_mask = state.movies[preferred_genres].max(axis=1) == 1
        candidate_items = state.movies[genre_mask]["item_id"]
    else:
        candidate_items = state.movies["item_id"]

    popular = (
        state.ratings[state.ratings["item_id"].isin(candidate_items)]
        .groupby("item_id")
        .agg(avg_rating=("rating", "mean"), count=("rating", "count"))
        .query("count >= 5")
        .sort_values(["avg_rating", "count"], ascending=[False, False])
    )
    return _build_recs_from_movie_scores(state, popular, count)


def recommend_cold_with_profile(
    state: AppState,
    age_code: int,
    gender: str,
    occupation_code: int,
    preferred_genres: list[str],
    count: int,
) -> tuple[list[MovieRecommendation], ColdPath, str, list[str]]:
    """Cold path for a brand-new user (UUID + supplied profile)."""
    cold = state.cold_start_model
    vec = encode_cold_user(
        age_code, gender, occupation_code, preferred_genres, cold["scaler"], cold["encoders"]
    )
    cluster = int(cold["kmeans"].predict([vec])[0])
    user_features: pd.DataFrame = cold["user_features"]
    cluster_users = (
        user_features[user_features["cluster"] == cluster].index.astype(int).tolist()
    )

    notes: list[str] = []

    if not cluster_users:
        recs = _fallback_genre_popular(state, preferred_genres, count)
        notes.append(
            f"cluster {cluster} had no users; used genre-popular fallback (FR-017)"
        )
        return (
            recs,
            "cold_fallback_genre_popular",
            "Cold-start fallback: most popular movies in your preferred genres",
            notes,
        )

    movie_scores = _aggregate_cluster(state, cluster_users, preferred_genres)
    recs = _build_recs_from_movie_scores(state, movie_scores, count)
    if len(recs) < count:
        notes.append(
            f"requested {count} but cluster {cluster} produced only {len(recs)} candidates"
        )
    return (
        recs,
        "cold_request_profile",
        f"Recommendations from cold-start model, similar to cluster {cluster}",
        notes,
    )


def recommend_cold_for_known_user(
    state: AppState,
    user_id_int: int,
    count: int,
) -> tuple[list[MovieRecommendation], ColdPath, str, list[str]]:
    """Cold path for a known low-rating-count user (research.md D-06)."""
    cold = state.cold_start_model
    user_features: pd.DataFrame = cold["user_features"]
    if user_id_int not in user_features.index:
        # Should not happen per data-model.md invariants; fall back gracefully.
        recs = _fallback_genre_popular(state, [], count)
        return (
            recs,
            "cold_fallback_genre_popular",
            "Cold-start fallback: user missing from cold-start model",
            [f"user {user_id_int} missing from cold_start_model['user_features']"],
        )

    cluster = int(user_features.loc[user_id_int, "cluster"])
    cluster_users = (
        user_features[user_features["cluster"] == cluster].index.astype(int).tolist()
    )
    movie_scores = _aggregate_cluster(state, cluster_users, preferred_genres=None)
    recs = _build_recs_from_movie_scores(state, movie_scores, count)

    notes: list[str] = []
    if len(recs) < count:
        notes.append(
            f"requested {count} but cluster {cluster} produced only {len(recs)} candidates"
        )
    return (
        recs,
        "cold_stored_demographics",
        f"Recommendations from cold-start model using stored demographics (cluster {cluster})",
        notes,
    )

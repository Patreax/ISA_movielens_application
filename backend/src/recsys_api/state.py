"""AppState — single immutable container shared across all requests.

Built once by the FastAPI lifespan handler. All fields are read-only after
startup (Constitution III, data-model.md invariants).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pandas as pd
from loguru import logger
from surprise import SVD

from .config import Settings
from .constants import GENRE_NAMES
from .data_loader import load_movies, load_ratings, load_users
from .model_loader import load_cold_start, load_svd


@dataclass(frozen=False)
class AppState:
    config: Settings
    movies: pd.DataFrame
    users: pd.DataFrame
    ratings: pd.DataFrame
    svd_model: SVD
    cold_start_model: dict[str, Any]

    known_user_ids: set[int] = field(default_factory=set)
    rating_counts: dict[int, int] = field(default_factory=dict)
    user_rated_items: dict[int, set[int]] = field(default_factory=dict)
    all_item_ids: list[int] = field(default_factory=list)
    title_by_item: dict[int, str] = field(default_factory=dict)
    genres_by_item: dict[int, list[str]] = field(default_factory=dict)


def build_state(settings: Settings) -> AppState:
    """Load every artefact, derive the lookup caches, return AppState."""
    data_dir = settings.data_dir
    models_dir = settings.models_dir

    movies = load_movies(data_dir / "movies.dat")
    users = load_users(data_dir / "users.dat").set_index("user_id", drop=False)
    ratings = load_ratings(data_dir / "ratings.dat")
    svd_model = load_svd(models_dir / "svd_model.pkl")
    cold_start_model = load_cold_start(models_dir / "cold_start_model.pkl")

    known_user_ids: set[int] = set(users.index.astype(int).tolist())
    rating_counts: dict[int, int] = (
        ratings.groupby("user_id").size().astype(int).to_dict()
    )
    user_rated_items: dict[int, set[int]] = (
        ratings.groupby("user_id")["item_id"].apply(set).to_dict()
    )
    all_item_ids: list[int] = movies["item_id"].astype(int).tolist()
    title_by_item: dict[int, str] = (
        movies.set_index("item_id")["title"].to_dict()
    )

    genre_cols = movies[["item_id", *GENRE_NAMES]].set_index("item_id")
    genres_by_item: dict[int, list[str]] = {
        int(item_id): [g for g in GENRE_NAMES if int(row[g]) == 1]
        for item_id, row in genre_cols.iterrows()
    }

    state = AppState(
        config=settings,
        movies=movies,
        users=users,
        ratings=ratings,
        svd_model=svd_model,
        cold_start_model=cold_start_model,
        known_user_ids=known_user_ids,
        rating_counts=rating_counts,
        user_rated_items=user_rated_items,
        all_item_ids=all_item_ids,
        title_by_item=title_by_item,
        genres_by_item=genres_by_item,
    )
    logger.info(
        f"AppState built: {len(movies)} movies, {len(users)} users, "
        f"{len(ratings)} ratings, {len(known_user_ids)} known user_ids."
    )
    return state

"""Load MovieLens-1M .dat files into pandas DataFrames.

Faithfully reproduces project1.dataset.load_{ratings,users,items} (research.md D-07).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from loguru import logger

from .constants import AGE_MAP, GENRE_NAMES, OCCUPATION_MAP


def load_movies(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="::",
        names=["item_id", "title", "genres_str"],
        engine="python",
        encoding="latin-1",
    )
    for genre in GENRE_NAMES:
        df[genre] = df["genres_str"].apply(lambda g, gn=genre: int(gn in g.split("|")))
    logger.info(f"Loaded {len(df)} movies from {path}")
    return df


def load_users(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="::",
        names=["user_id", "gender", "age_code", "occupation_code", "zip_code"],
        engine="python",
        encoding="latin-1",
    )
    df["age_label"] = df["age_code"].map(AGE_MAP)
    df["occupation"] = df["occupation_code"].map(OCCUPATION_MAP)
    logger.info(f"Loaded {len(df)} users from {path}")
    return df


def load_ratings(path: Path) -> pd.DataFrame:
    df = pd.read_csv(
        path,
        sep="::",
        names=["user_id", "item_id", "rating", "timestamp"],
        engine="python",
        encoding="latin-1",
    )
    logger.info(f"Loaded {len(df)} ratings from {path}")
    return df

"""Load and validate the two pretrained models (Constitution Principle III/IV).

Both loaders raise RuntimeError with a descriptive message on any structural
mismatch — Uvicorn lifespan propagates the exception, so the process exits
non-zero (no degraded startup).
"""
from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger
from sklearn.cluster import KMeans
from sklearn.preprocessing import LabelEncoder, StandardScaler
from surprise import SVD


def load_svd(path: Path) -> SVD:
    if not path.exists():
        raise RuntimeError(f"SVD model file not found: {path}")
    with open(path, "rb") as f:
        obj = pickle.load(f)
    if not isinstance(obj, SVD):
        raise RuntimeError(
            f"svd_model.pkl is not a surprise.SVD instance (got {type(obj).__name__})"
        )
    logger.info(f"Loaded SVD model from {path}")
    return obj


_REQUIRED_COLD_KEYS = {"kmeans", "scaler", "encoders", "user_features"}


def load_cold_start(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RuntimeError(f"Cold-start model file not found: {path}")
    with open(path, "rb") as f:
        obj = pickle.load(f)
    if not isinstance(obj, dict):
        raise RuntimeError(
            f"cold_start_model.pkl is not a dict (got {type(obj).__name__})"
        )
    missing = _REQUIRED_COLD_KEYS - set(obj.keys())
    if missing:
        raise RuntimeError(
            f"cold_start_model.pkl missing required keys: {sorted(missing)}"
        )
    if not isinstance(obj["kmeans"], KMeans):
        raise RuntimeError(
            f"cold_start_model['kmeans'] is not sklearn KMeans (got {type(obj['kmeans']).__name__})"
        )
    if not isinstance(obj["scaler"], StandardScaler):
        raise RuntimeError(
            "cold_start_model['scaler'] is not sklearn StandardScaler "
            f"(got {type(obj['scaler']).__name__})"
        )
    encoders = obj["encoders"]
    if not isinstance(encoders, dict) or "gender" not in encoders:
        raise RuntimeError(
            "cold_start_model['encoders'] must be a dict with a 'gender' entry"
        )
    if not isinstance(encoders["gender"], LabelEncoder):
        raise RuntimeError(
            "cold_start_model['encoders']['gender'] is not sklearn LabelEncoder "
            f"(got {type(encoders['gender']).__name__})"
        )
    user_features = obj["user_features"]
    if not isinstance(user_features, pd.DataFrame):
        raise RuntimeError(
            "cold_start_model['user_features'] is not a pandas DataFrame "
            f"(got {type(user_features).__name__})"
        )
    if "cluster" not in user_features.columns:
        raise RuntimeError(
            "cold_start_model['user_features'] DataFrame is missing 'cluster' column"
        )
    logger.info(
        f"Loaded cold-start model from {path} "
        f"(n_clusters={obj['kmeans'].n_clusters}, "
        f"user_features.shape={user_features.shape})"
    )
    return obj

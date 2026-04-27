"""Cold-start feature encoding (adapted from project1.features.encode_cold_user)."""
from __future__ import annotations

import numpy as np
from sklearn.preprocessing import LabelEncoder, StandardScaler

from .constants import GENRE_NAMES


def encode_cold_user(
    age_code: int,
    gender: str,
    occupation_code: int,
    preferred_genres: list[str],
    scaler: StandardScaler,
    encoders: dict[str, LabelEncoder],
) -> np.ndarray:
    """Encode a cold-start profile into the same feature space as existing users.

    Mirrors `project1.features.encode_cold_user` exactly:
      [age_code, gender_enc, occupation_code] + 18 genre-preference values
      where each genre value is 5.0 if listed in preferred_genres else 0.0.
    """
    gender_enc = encoders["gender"].transform([gender])[0]
    genre_vector = [5.0 if g in preferred_genres else 0.0 for g in GENRE_NAMES]
    raw = [age_code, gender_enc, occupation_code] + genre_vector
    scaled = scaler.transform([raw])
    return scaled[0]

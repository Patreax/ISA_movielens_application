"""Settings loaded from environment variables (research.md D-11)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="RECSYS_API_",
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    host: str = Field(default="0.0.0.0", description="Uvicorn bind host")
    port: int = Field(default=8000, description="Uvicorn bind port")
    data_dir: Path = Field(
        default=Path("/app/data/ml-1m"),
        description="Directory containing movies.dat, users.dat, ratings.dat",
    )
    models_dir: Path = Field(
        default=Path("/app/models"),
        description="Directory containing svd_model.pkl, cold_start_model.pkl",
    )
    rating_threshold: int = Field(
        default=5,
        ge=1,
        description="Min ratings for a known user to use the warm path (FR-006).",
    )
    cors_origins: str = Field(
        default="*",
        description="Comma-separated list of allowed CORS origins, or '*'.",
    )
    log_level: str = Field(default="INFO", description="loguru log level.")

    def cors_origins_list(self) -> list[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

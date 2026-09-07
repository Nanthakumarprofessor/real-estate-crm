"""
Application settings loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""
from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str

    # ── JWT ───────────────────────────────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # ── Application ───────────────────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = False

    # CORS origins — comma-separated string or a list
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("jwt_secret_key")
    @classmethod
    def secret_key_must_not_be_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("JWT_SECRET_KEY must not be empty")
        return v

    @field_validator("database_url")
    @classmethod
    def database_url_must_not_be_empty(cls, v: str) -> str:
        if not v or v.strip() == "":
            raise ValueError("DATABASE_URL must not be empty")
        return v

    @property
    def cors_origins(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list of origin strings."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return a cached Settings instance.
    lru_cache ensures the .env file is only read once per process lifetime.
    """
    return Settings()

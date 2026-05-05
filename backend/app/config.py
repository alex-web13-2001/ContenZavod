"""ContenZavod application configuration.

All settings are loaded from environment variables with sensible defaults.
Uses Pydantic Settings for validation and type coercion.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ───────────────────────────────
    app_name: str = "ContenZavod"
    app_env: str = "development"
    app_debug: bool = True
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    log_level: str = "INFO"

    # ── Database ──────────────────────────────────
    database_url: str = "postgresql+asyncpg://cz_user:devpassword@postgres:5432/contenzavod"

    postgres_pool_size: int = 20
    postgres_max_overflow: int = 10
    postgres_pool_timeout: int = 30

    # ── Redis ─────────────────────────────────────
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # ── MinIO ─────────────────────────────────────
    minio_endpoint: str = "minio:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "contenzavod"
    minio_use_ssl: bool = False

    # ── Auth ──────────────────────────────────────
    jwt_secret_key: str = "changeme_jwt_secret_at_least_32_chars"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 1440  # 24 hours
    jwt_refresh_token_expire_days: int = 30

    # ── AI Providers ──────────────────────────────
    gemini_api_key: str = ""
    kie_api_key: str = ""  # KIE.ai API — Claude Haiku 4.5
    kling_access_key: str = ""
    kling_secret_key: str = ""

    # ── ReVid (Video Digest) ──────────────────────
    revid_api_key: str = ""
    revid_voice_id: str = "Qvbf0AoA7UZSgJUp8Ba5"
    revid_avatar_url: str = ""   # Public URL of the avatar image
    revid_aspect_ratio: str = "9:16"
    revid_quality: str = "pro"

    # ── CORS ──────────────────────────────────────
    cors_origins: list[str] = ["*"]

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.strip("[]").replace('"', "").split(",")]
        return v

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

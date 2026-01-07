"""
Application settings and configuration management.
Uses pydantic-settings for environment variable loading.
"""

from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Sentiment Recommendation System"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"

    # API Settings
    api_prefix: str = "/api/v1"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # PostgreSQL Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "test"
    postgres_password: str = "testPass123"
    postgres_db: str = "test_db"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def database_url_sync(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0

    @property
    def redis_url(self) -> str:
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    # Celery
    celery_broker_url: Optional[str] = None
    celery_result_backend: Optional[str] = None

    @property
    def celery_broker(self) -> str:
        return self.celery_broker_url or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.celery_result_backend or self.redis_url

    # Qdrant Vector Database
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_vehicles: str = "vehicles"
    qdrant_collection_livreurs: str = "livreurs"

    # Embedding Model
    embedding_model_name: str = "paraphrase-multilingual-mpnet-base-v2"
    embedding_dimension: int = 768

    # Sentiment Model (Module 1)
    sentiment_model_path: str = "./models/distil-camembert-sentiment"

    # Recommendation Settings
    default_top_k: int = 10
    similarity_weight: float = 0.6
    availability_weight: float = 0.25
    reputation_weight: float = 0.15
    cache_ttl_seconds: int = 3600
    sentiment_score_tolerance: float = 0.1

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60

    # Security
    secret_key: str = "maclésecrete"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Logging
    log_level: str = "INFO"
    log_format: str = "json"

    # Monitoring - Elastic APM
    apm_enabled: bool = True
    apm_server_url: str = "http://localhost:8200"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()

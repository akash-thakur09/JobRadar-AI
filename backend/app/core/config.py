"""Application configuration module using Pydantic Settings."""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_cors_origins(v: str | list[str]) -> list[str]:
    """Parse CORS origins if provided as a comma-separated string or list."""
    if isinstance(v, str):
        import json

        # Support JSON array format or comma-separated strings
        val = v.strip()
        if val.startswith("[") and val.endswith("]"):
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except json.JSONDecodeError:
                pass
        return [origin.strip() for origin in val.split(",") if origin.strip()]
    return v


CorsOrigins = Annotated[list[str], BeforeValidator(_parse_cors_origins)]


class Settings(BaseSettings):
    """Core application settings validated from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Core Application
    app_name: str = Field(default="JobRadar AI", description="Application name")
    app_env: Literal["development", "staging", "production", "test"] = Field(
        default="development", description="Execution environment"
    )
    debug: bool = Field(default=True, description="Debug mode toggle")
    log_level: str = Field(default="INFO", description="Standard logging level")
    host: str = Field(default="0.0.0.0", description="API server host")
    port: int = Field(default=8000, description="API server port")
    api_v1_prefix: str = Field(default="/api/v1", description="API v1 routing prefix")

    # Security & CORS
    cors_origins: CorsOrigins = Field(
        default_factory=lambda: ["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # PostgreSQL Relational Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/jobradar_ai",
        description="Asynchronous PostgreSQL connection URL",
    )
    database_sync_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/jobradar_ai",
        description="Synchronous PostgreSQL connection URL for Alembic migrations",
    )
    database_pool_size: int = Field(default=10, description="Database connection pool size")
    database_max_overflow: int = Field(default=20, description="Max database overflow connections")
    database_pool_timeout: int = Field(default=30, description="Database pool timeout in seconds")

    # Redis Infrastructure
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching and locks",
    )

    # Celery Background Processing
    celery_broker_url: str = Field(
        default="redis://localhost:6379/1",
        description="Celery message broker URL",
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/2",
        description="Celery task result backend URL",
    )

    # LLM & Semantic Analysis
    llm_provider: str = Field(
        default="ollama",
        description="LLM provider implementation ('ollama', 'mock')",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Local Ollama instance base URL",
    )
    ollama_model: str = Field(
        default="llama3.1:8b",
        description="Default local LLM model name",
    )
    llm_timeout_seconds: float = Field(
        default=30.0,
        description="Timeout for LLM generation in seconds",
    )
    llm_max_retries: int = Field(
        default=2,
        description="Maximum retries for LLM requests",
    )
    llm_temperature: float = Field(
        default=0.1,
        description="LLM sampling temperature",
    )
    tailoring_max_regeneration_attempts: int = Field(
        default=2,
        description="Maximum regeneration attempts on claim validation failure",
    )

    # Local File Storage
    storage_dir: str = Field(
        default="storage",
        description="Root directory for local file storage",
    )

    # Email Notification & Delivery (Milestone 9)
    email_provider: str = Field(
        default="smtp",
        description="Email provider implementation ('smtp', 'mock')",
    )
    smtp_host: str = Field(default="localhost", description="Outbound SMTP hostname")
    smtp_port: int = Field(default=1025, description="Outbound SMTP port")
    smtp_username: str = Field(default="", description="SMTP username")
    smtp_user: str = Field(default="", description="Legacy alias for SMTP username")
    smtp_password: str = Field(default="", description="SMTP password")
    smtp_from_email: str = Field(
        default="notifications@jobradar.ai",
        description="Outbound sender email address",
    )
    smtp_from_name: str = Field(
        default="JobRadar AI",
        description="Outbound sender display name",
    )
    smtp_use_tls: bool = Field(default=False, description="Enable TLS/STARTTLS for SMTP connection")
    smtp_timeout_seconds: float = Field(
        default=15.0,
        description="SMTP connection and socket timeout in seconds",
    )
    email_max_retries: int = Field(
        default=3,
        description="Maximum retry attempts for transient email failures",
    )
    email_retry_backoff: float = Field(
        default=10.0,
        description="Base retry backoff seconds for email tasks",
    )

    @property
    def effective_smtp_username(self) -> str:
        """Resolve effective SMTP username considering both smtp_username and legacy smtp_user."""
        return self.smtp_username or self.smtp_user

    @property
    def is_production(self) -> bool:
        """Helper to check if running in production."""
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        """Helper to check if running in test environment."""
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings instance."""
    return Settings()

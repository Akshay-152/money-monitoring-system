"""Environment-driven application settings."""
from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Centralize runtime configuration so deployment does not require code edits."""

    database_path: str = os.getenv("DATABASE_PATH", "data/flux.db")
    storage_backend: str = os.getenv("STORAGE_BACKEND", "sqlite")
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    frontend_origin: str = os.getenv("FRONTEND_ORIGIN", "*")
    llm_fallback_enabled: bool = os.getenv("LLM_FALLBACK_ENABLED", "false").lower() == "true"
    pubsub_audience: str = os.getenv("PUBSUB_AUDIENCE", "")
    environment: str = os.getenv("FLASK_ENV", "development")


settings = Settings()

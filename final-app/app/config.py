"""Application configuration via pydantic-settings.

Loaded once at import time. Layering:
  1. Class defaults
  2. .env file
  3. Process environment variables
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="ENROLLMENT_",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Subject Enrollment Service"
    app_version: str = "1.0.0"
    api_prefix: str = "/api/v1"

    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
    log_level: str = "INFO"

    db_url: str = "sqlite+aiosqlite:///./enrollment.db"

    secret_key: str = "training-default-secret-32-chars-min-replace-me"
    access_token_minutes: int = 60
    refresh_token_days: int = 7

    default_list_limit: int = 50
    slow_request_ms: int = 500

    @property
    def db_dialect(self) -> str:
        return self.db_url.split(":", 1)[0].split("+", 1)[0]

    def safe_dump(self) -> dict:
        """Returns config without secrets — safe to log on startup."""
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "log_level": self.log_level,
            "api_prefix": self.api_prefix,
            "db_dialect": self.db_dialect,
            "cors_origins": self.cors_origins,
            "default_list_limit": self.default_list_limit,
        }


settings = Settings()

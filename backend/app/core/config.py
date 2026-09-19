"""Application configuration.

Settings are read from environment variables, falling back to a local ``.env``
file and finally to the defaults declared below. A single cached
:class:`Settings` instance is exposed via :func:`get_settings` so that the
values are parsed once per process and can be overridden in tests.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Repository-relative anchor: <repo>/backend
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Runtime configuration for the Community Intelligence API."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Service identity ---------------------------------------------------
    service_name: str = "community-intelligence-api"
    environment: str = "development"
    debug: bool = True

    # --- Database -----------------------------------------------------------
    database_url: str = "sqlite:///./data/community.db"
    database_echo: bool = False

    # --- External data sources ----------------------------------------------
    # Held as SecretStr so the value is masked in reprs, logs and tracebacks;
    # read it deliberately with ``.get_secret_value()`` at the call site.
    # Optional: the Census API serves up to 500 requests per day unkeyed, so
    # the app must boot and the test suite must pass without it.
    census_api_key: SecretStr | None = Field(
        default=None,
        description="US Census Data API key. Never commit this value.",
    )

    # --- CORS ---------------------------------------------------------------
    # Stored as a raw string rather than ``list[str]`` on purpose:
    # pydantic-settings parses complex types as JSON, which would reject the
    # comma-separated form that is far friendlier in a .env file or a shell.
    # Vite's dev server increments its port when 5173 is already in use, so
    # 5174 and 5175 are allowed too. Without them the frontend silently falls
    # back to its demo data, which looks exactly like the backend being down -
    # an expensive thing to debug during a live demo. Still an explicit list
    # rather than a wildcard.
    cors_origins: str = Field(
        default=(
            "http://localhost:5173,http://127.0.0.1:5173,"
            "http://localhost:5174,http://127.0.0.1:5174,"
            "http://localhost:5175,http://127.0.0.1:5175"
        ),
        description="Comma-separated browser origins permitted to call this API.",
    )

    @field_validator("cors_origins")
    @classmethod
    def _reject_blank_origins(cls, value: str) -> str:
        """Guard against a silently CORS-disabled API from an empty env var."""
        if not value.strip():
            raise ValueError(
                "CORS_ORIGINS must not be empty; the frontend cannot call the "
                "API without at least one allowed origin."
            )
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        """``cors_origins`` split into a list, ignoring blanks and whitespace."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_sqlite(self) -> bool:
        """Whether the configured database is SQLite."""
        return self.database_url.startswith("sqlite")

    @property
    def has_census_api_key(self) -> bool:
        """Whether a Census API key is configured.

        Lets calling code branch on availability without ever unwrapping the
        secret just to test it for emptiness.
        """
        return bool(self.census_api_key and self.census_api_key.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings instance.

    Cached so that the ``.env`` file is read once. Tests that need different
    values should call ``get_settings.cache_clear()`` after patching the
    environment.
    """
    return Settings()

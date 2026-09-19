"""Tests for application configuration, including secret handling.

The secret tests are deliberate regression guards: a credential that leaks into
a tracked file or a log line is expensive to undo, and the mistakes that cause
it (pasting a real value into the template, printing a settings object) are
easy to make and quiet when they happen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import BACKEND_DIR, Settings
from app.core.database import _normalise_sqlite_url

ENV_EXAMPLE: Path = BACKEND_DIR / ".env.example"

# Assignments in .env.example that must never ship with a value filled in.
SECRET_KEYS: tuple[str, ...] = ("CENSUS_API_KEY",)


def _env_example_lines() -> list[str]:
    return ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()


def test_env_example_exists() -> None:
    """The committed template is what new contributors copy from."""
    assert ENV_EXAMPLE.is_file()


@pytest.mark.parametrize("key", SECRET_KEYS)
def test_env_example_secrets_are_blank(key: str) -> None:
    """No secret in the tracked template may carry a real value."""
    for line in _env_example_lines():
        stripped = line.strip()
        if stripped.startswith(f"{key}="):
            value = stripped.split("=", 1)[1].strip()
            assert value == "", (
                f"{key} in .env.example must be blank, but has a value. "
                "Real credentials belong in .env, which is gitignored."
            )


def test_env_example_contains_no_long_hex_literals() -> None:
    """Catch a pasted credential even under an unexpected variable name."""
    text = ENV_EXAMPLE.read_text(encoding="utf-8")
    suspects = re.findall(r"\b[0-9a-fA-F]{32,}\b", text)
    assert not suspects, f".env.example contains {len(suspects)} secret-like literal(s)."


def test_census_api_key_is_masked_in_repr() -> None:
    """SecretStr keeps the key out of reprs, logs and tracebacks."""
    sentinel = "sentinel-not-a-real-key"
    settings = Settings(census_api_key=sentinel)

    assert sentinel not in repr(settings)
    assert sentinel not in str(settings)
    # The value is still retrievable when explicitly unwrapped.
    assert settings.census_api_key is not None
    assert settings.census_api_key.get_secret_value() == sentinel


def test_census_api_key_is_optional() -> None:
    """The app must boot without a key; the Census API allows unkeyed use."""
    settings = Settings(_env_file=None, census_api_key=None)

    assert settings.census_api_key is None
    assert settings.has_census_api_key is False


def test_has_census_api_key_rejects_whitespace() -> None:
    """A key of only whitespace counts as absent, not present."""
    assert Settings(census_api_key="   ").has_census_api_key is False
    assert Settings(census_api_key="abc").has_census_api_key is True


def test_cors_origins_parsed_as_comma_separated_list() -> None:
    """Comma-separated parsing, tolerating whitespace and trailing commas."""
    settings = Settings(cors_origins="http://a.test, http://b.test ,")

    assert settings.cors_origin_list == ["http://a.test", "http://b.test"]


def test_blank_cors_origins_rejected() -> None:
    """An empty origins list yields an API no browser can call."""
    with pytest.raises(ValidationError):
        Settings(cors_origins="   ")


def test_relative_sqlite_url_is_anchored_to_backend_directory() -> None:
    """The populated snapshot must be identical from any process cwd."""
    url = _normalise_sqlite_url("sqlite:///./data/community.db")

    assert url == f"sqlite:///{(BACKEND_DIR / 'data/community.db').resolve()}"


def test_memory_sqlite_url_is_unchanged() -> None:
    """Test databases and SQLite memory URLs must not be rewritten."""
    assert _normalise_sqlite_url("sqlite:///:memory:") == "sqlite:///:memory:"

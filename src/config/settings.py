"""
Application settings - pydantic-settings configuration.

This module defines application configuration using pydantic-settings
for environment variable loading with validation and defaults.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Database configuration
    database_url: str = "postgresql://beefirst:beefirst@localhost:5432/beefirst"
    pool_min_size: int = 2  # Minimum connections in pool
    pool_max_size: int = 10  # Maximum connections in pool

    # Registration settings
    ttl_seconds: int = 60  # Verification window duration
    max_attempts: int = 3  # Max failed verification attempts before lockout

    # Security settings
    bcrypt_cost: int = 10  # bcrypt work factor (≥10 per NFR-S1)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

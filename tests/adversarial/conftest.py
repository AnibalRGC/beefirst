"""
Shared fixtures for adversarial tests.

Provides common test infrastructure for race condition and brute force tests.
"""

from collections.abc import Generator

import bcrypt
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.config.settings import get_settings

# Module-level marker for all adversarial tests
pytestmark = pytest.mark.adversarial


@pytest.fixture(scope="module")
def pool() -> Generator[ConnectionPool, None, None]:
    """Create connection pool for adversarial tests."""
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        open=True,
    )
    yield pool
    pool.close()


@pytest.fixture
def repository(pool: ConnectionPool) -> PostgresRegistrationRepository:
    """Create repository instance for each test."""
    return PostgresRegistrationRepository(pool)


@pytest.fixture(autouse=True)
def clean_database(pool: ConnectionPool) -> Generator[None, None, None]:
    """Clean registrations table before each test."""
    with pool.connection() as conn:
        conn.execute("DELETE FROM registrations")
        conn.commit()
    yield


def create_registration(
    pool: ConnectionPool, email: str, password: str, code: str
) -> None:
    """Helper to create a CLAIMED registration."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
    with pool.connection() as conn:
        conn.execute(
            "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
            (email, password_hash, code),
        )
        conn.commit()

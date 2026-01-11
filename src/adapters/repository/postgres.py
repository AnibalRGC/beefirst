"""
PostgreSQL repository adapter - Implements RegistrationRepository protocol.

This module provides the PostgreSQL implementation of the domain's
repository port using psycopg3 with raw SQL.
"""

import logging
from pathlib import Path

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


class PostgresRegistrationRepository:
    """
    Implements RegistrationRepository protocol via psycopg3.

    Uses structural subtyping - no explicit inheritance from Protocol.
    All SQL uses parameterized queries for security.
    """

    def __init__(self, pool: ConnectionPool) -> None:
        """
        Initialize repository with connection pool.

        Args:
            pool: psycopg3 ConnectionPool for database connections
        """
        self._pool = pool

    def claim_email(self, email: str, password_hash: str, code: str) -> bool:
        """
        Atomically claim an email address for registration.

        Uses INSERT ... ON CONFLICT DO NOTHING for atomic claim.
        The database UNIQUE constraint on email ensures no race conditions.

        Args:
            email: Normalized email address (lowercase, stripped)
            password_hash: bcrypt-hashed password from domain layer
            code: 4-digit verification code

        Returns:
            True if claim successful, False if email already claimed
        """
        sql = """
            INSERT INTO registrations (email, password_hash, verification_code)
            VALUES (%s, %s, %s)
            ON CONFLICT (email) DO NOTHING
        """

        with self._pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, code))
            conn.commit()
            return cursor.rowcount == 1


def run_migrations(pool: ConnectionPool) -> None:
    """
    Execute all SQL migration files from the migrations directory.

    Migrations are executed in sorted order (alphabetically by filename).
    Each migration should be idempotent (use IF NOT EXISTS, etc.).

    Args:
        pool: psycopg3 ConnectionPool instance
    """
    # Find migrations directory relative to this file
    # Structure: src/adapters/repository/postgres.py -> migrations/
    migrations_dir = Path(__file__).parent.parent.parent.parent / "migrations"

    if not migrations_dir.exists():
        logger.warning(f"Migrations directory not found: {migrations_dir}")
        return

    sql_files = sorted(migrations_dir.glob("*.sql"))

    if not sql_files:
        logger.info("No migration files found")
        return

    logger.info(f"Running {len(sql_files)} migration(s)")

    for sql_file in sql_files:
        logger.info(f"Executing migration: {sql_file.name}")
        try:
            sql_content = sql_file.read_text()

            with pool.connection() as conn:
                conn.execute(sql_content)
                # psycopg3 auto-commits by default

            logger.info(f"Migration complete: {sql_file.name}")
        except Exception as e:
            logger.error(f"Migration failed: {sql_file.name} - {e}")
            raise RuntimeError(f"Database migration failed: {sql_file.name}") from e

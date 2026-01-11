"""
PostgreSQL repository adapter - Implements RegistrationRepository protocol.

This module provides the PostgreSQL implementation of the domain's
repository port using psycopg3 with raw SQL.

Full repository implementation in Story 2.2.
"""

import logging
from pathlib import Path

from psycopg_pool import ConnectionPool

logger = logging.getLogger(__name__)


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
        sql_content = sql_file.read_text()

        with pool.connection() as conn:
            conn.execute(sql_content)
            # No explicit commit needed - migrations contain BEGIN...COMMIT

        logger.info(f"Migration complete: {sql_file.name}")

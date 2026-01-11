"""
PostgreSQL repository adapter - Implements RegistrationRepository protocol.

This module provides the PostgreSQL implementation of the domain's
repository port using psycopg3 with raw SQL.

Security Design - Timing Oracle Prevention:
------------------------------------------
The verify_and_activate method implements constant-time operations to prevent
timing oracle attacks that could reveal information about account existence
or credential validity:

1. **bcrypt.checkpw()**: Used for password verification. bcrypt's built-in
   comparison is constant-time (~100ms with cost factor 10), which dominates
   response time and masks other timing variations.

2. **secrets.compare_digest()**: Used for verification code comparison.
   Explicitly mitigates timing attacks on the 4-digit code.

3. **_DUMMY_BCRYPT_HASH**: When an email doesn't exist or password_hash is NULL
   (locked accounts), we compare against a pre-computed dummy hash to ensure
   bcrypt always runs. This prevents attackers from detecting account existence
   through response time differences.

4. **Execution Order**: Both cryptographic comparisons ALWAYS execute before
   any state-based return. No early returns bypass the constant-time operations.

References:
- [Source: architecture.md#Authentication & Security]
- [Source: prd.md#NFR-S2 (Constant-time password verification)]
- [Source: prd.md#NFR-P3 (Consistent error timing)]
"""

import logging
import secrets
from pathlib import Path

import bcrypt
from psycopg_pool import ConnectionPool

from src.domain.ports import TrustState, VerifyResult

logger = logging.getLogger(__name__)

# Pre-computed bcrypt hash for timing oracle prevention.
# Used when email doesn't exist to ensure constant-time password comparison.
# Hash of "dummy_password_for_timing_safety" with cost factor 10.
_DUMMY_BCRYPT_HASH = bcrypt.hashpw(b"dummy_password_for_timing_safety", bcrypt.gensalt(10)).decode()


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

        Supports re-registration for EXPIRED and LOCKED emails (FR17).
        ACTIVE and CLAIMED emails cannot be re-registered.

        Uses INSERT ... ON CONFLICT DO UPDATE WHERE for atomic upsert.
        The WHERE clause ensures only EXPIRED/LOCKED states are overwritten.
        The database UNIQUE constraint on email ensures no race conditions (FR18).

        Args:
            email: Normalized email address (lowercase, stripped)
            password_hash: bcrypt-hashed password from domain layer
            code: 4-digit verification code

        Returns:
            True if claim successful (new registration or re-registration),
            False if email already claimed (ACTIVE or CLAIMED state)
        """
        sql = """
            INSERT INTO registrations (email, password_hash, verification_code, state, attempt_count, created_at)
            VALUES (%s, %s, %s, 'CLAIMED', 0, NOW())
            ON CONFLICT (email) DO UPDATE
            SET password_hash = EXCLUDED.password_hash,
                verification_code = EXCLUDED.verification_code,
                state = 'CLAIMED',
                attempt_count = 0,
                created_at = NOW(),
                activated_at = NULL
            WHERE registrations.state IN ('EXPIRED', 'LOCKED')
        """

        with self._pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(sql, (email, password_hash, code))
            conn.commit()
            # Returns 1 if INSERT succeeded OR UPDATE WHERE matched (EXPIRED/LOCKED only)
            return cursor.rowcount == 1

    def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
        """
        Verify code and password, activate account if valid.

        Uses SELECT FOR UPDATE to lock the row during verification,
        preventing race conditions in concurrent activation attempts.

        Security measures:
        - Constant-time code comparison via secrets.compare_digest()
        - Constant-time password verification via bcrypt.checkpw()
        - Dummy hash comparison for non-existent emails (timing oracle prevention)
        - Generic INVALID_CODE for both code and password failures

        Args:
            email: Normalized email address
            code: 4-digit verification code
            password: User's plaintext password

        Returns:
            VerifyResult indicating success or specific failure reason
        """
        # SQL to fetch and lock registration row
        select_sql = """
            SELECT password_hash, verification_code, state, attempt_count, created_at
            FROM registrations
            WHERE email = %s
            FOR UPDATE
        """

        # SQL to activate account
        activate_sql = """
            UPDATE registrations
            SET state = %s, activated_at = NOW()
            WHERE email = %s AND state = %s
        """

        # SQL to increment attempt count
        increment_sql = """
            UPDATE registrations
            SET attempt_count = attempt_count + 1
            WHERE email = %s AND state = %s
        """

        # SQL to lock account (3 failures)
        lock_sql = """
            UPDATE registrations
            SET state = %s, attempt_count = attempt_count + 1, password_hash = NULL
            WHERE email = %s AND state = %s
        """

        with self._pool.connection() as conn, conn.cursor() as cursor:
            # Fetch registration with row lock
            cursor.execute(select_sql, (email,))
            row = cursor.fetchone()

            # Prepare values for constant-time comparison
            # Use dummy values if registration not found to prevent timing oracle
            if row is not None:
                # CRITICAL: password_hash may be NULL for LOCKED accounts (Data Stewardship)
                # Use dummy hash to maintain constant-time comparison
                stored_hash = row[0] if row[0] is not None else _DUMMY_BCRYPT_HASH
                stored_code = row[1]
                state = row[2]
                attempt_count = row[3]
                # created_at = row[4]  # TTL checked in SQL below
            else:
                stored_hash = _DUMMY_BCRYPT_HASH
                stored_code = "0000"
                state = None
                attempt_count = 0

            # CRITICAL: Always run BOTH comparisons for constant-time behavior
            # This prevents timing oracle attacks that could reveal information
            code_valid = secrets.compare_digest(stored_code.encode(), code.encode())
            password_valid = bcrypt.checkpw(password.encode(), stored_hash.encode())

            # Now process results - check state-based returns after constant-time ops
            if row is None:
                conn.commit()
                return VerifyResult.NOT_FOUND

            # LOCKED state returns LOCKED (account was locked due to 3 failures)
            if state == TrustState.LOCKED.value:
                conn.commit()
                return VerifyResult.LOCKED

            # Any state other than CLAIMED (e.g., ACTIVE, EXPIRED) returns NOT_FOUND
            if state != TrustState.CLAIMED.value:
                conn.commit()
                return VerifyResult.NOT_FOUND

            # Check TTL (60-second window) using database time
            ttl_sql = """
                SELECT 1 FROM registrations
                WHERE email = %s
                  AND state = %s
                  AND created_at > NOW() - INTERVAL '60 seconds'
            """
            cursor.execute(ttl_sql, (email, TrustState.CLAIMED.value))
            if cursor.fetchone() is None:
                # Lazy transition: CLAIMED → EXPIRED with credential purge (FR15, FR24)
                # Data Stewardship: No ghost credentials for expired accounts (FR25)
                expire_sql = """
                    UPDATE registrations
                    SET state = %s, password_hash = NULL
                    WHERE email = %s AND state = %s
                """
                cursor.execute(
                    expire_sql, (TrustState.EXPIRED.value, email, TrustState.CLAIMED.value)
                )
                conn.commit()
                return VerifyResult.EXPIRED

            # Check if already locked (3+ attempts)
            if attempt_count >= 3:
                conn.commit()
                return VerifyResult.LOCKED

            # Verify code and password
            if not code_valid or not password_valid:
                # Increment attempt count
                new_attempt_count = attempt_count + 1

                if new_attempt_count >= 3:
                    # Lock account and purge password hash (Data Stewardship)
                    cursor.execute(
                        lock_sql,
                        (TrustState.LOCKED.value, email, TrustState.CLAIMED.value),
                    )
                    conn.commit()
                    return VerifyResult.LOCKED
                else:
                    # Just increment attempt count
                    cursor.execute(increment_sql, (email, TrustState.CLAIMED.value))
                    conn.commit()
                    return VerifyResult.INVALID_CODE

            # All checks passed - activate account
            cursor.execute(
                activate_sql,
                (TrustState.ACTIVE.value, email, TrustState.CLAIMED.value),
            )
            conn.commit()
            return VerifyResult.SUCCESS


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

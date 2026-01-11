"""
Integration tests for PostgresRegistrationRepository.

Tests repository operations against a real PostgreSQL database.
Requires PostgreSQL to be running (via docker-compose).
"""

from concurrent.futures import ThreadPoolExecutor

import bcrypt
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.config.settings import get_settings
from src.domain.ports import VerifyResult


@pytest.fixture(scope="module")
def pool() -> ConnectionPool:
    """Create connection pool for integration tests."""
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
    )
    yield pool
    pool.close()


@pytest.fixture
def repository(pool: ConnectionPool) -> PostgresRegistrationRepository:
    """Create repository instance for each test."""
    return PostgresRegistrationRepository(pool)


@pytest.fixture(autouse=True)
def clean_database(pool: ConnectionPool) -> None:
    """Clean registrations table before each test."""
    with pool.connection() as conn:
        conn.execute("DELETE FROM registrations")
        conn.commit()
    yield


class TestClaimEmail:
    """Tests for claim_email method."""

    def test_claim_email_success_returns_true(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """Claiming an unclaimed email returns True."""
        result = repository.claim_email(
            email="test@example.com",
            password_hash="$2b$10$hashedpasswordvalue",
            code="1234",
        )
        assert result is True

    def test_claim_email_duplicate_returns_false(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """Claiming an already-claimed email returns False (not exception)."""
        # First claim succeeds
        result1 = repository.claim_email(
            email="duplicate@example.com",
            password_hash="$2b$10$hash1",
            code="1234",
        )
        assert result1 is True

        # Second claim for same email fails gracefully
        result2 = repository.claim_email(
            email="duplicate@example.com",
            password_hash="$2b$10$hash2",
            code="5678",
        )
        assert result2 is False

    def test_claim_different_emails_both_succeed(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """Claiming different emails both succeed."""
        result1 = repository.claim_email("user1@example.com", "$2b$10$hash1", "1111")
        result2 = repository.claim_email("user2@example.com", "$2b$10$hash2", "2222")

        assert result1 is True
        assert result2 is True


class TestClaimEmailRecordCreation:
    """Tests for record creation during claim_email."""

    def test_record_created_with_claimed_state(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Claimed record has state='CLAIMED'."""
        repository.claim_email("state@example.com", "$2b$10$hash", "1234")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                ("state@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "CLAIMED"

    def test_record_created_with_zero_attempt_count(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Claimed record has attempt_count=0."""
        repository.claim_email("attempts@example.com", "$2b$10$hash", "1234")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count FROM registrations WHERE email = %s",
                ("attempts@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == 0

    def test_record_stores_password_hash(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Password hash is stored correctly."""
        expected_hash = "$2b$10$specifichashedvalue"
        repository.claim_email("hash@example.com", expected_hash, "1234")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                ("hash@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == expected_hash

    def test_record_stores_verification_code(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Verification code is stored correctly."""
        repository.claim_email("code@example.com", "$2b$10$hash", "9876")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT verification_code FROM registrations WHERE email = %s",
                ("code@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "9876"

    def test_record_has_created_at_timestamp(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Claimed record has created_at timestamp set by database."""
        repository.claim_email("timestamp@example.com", "$2b$10$hash", "1234")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT created_at FROM registrations WHERE email = %s",
                ("timestamp@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] is not None  # Timestamp should be set


class TestConcurrentClaims:
    """Tests for concurrent email claim handling."""

    def test_concurrent_claims_exactly_one_succeeds(self, pool: ConnectionPool) -> None:
        """When two concurrent claims for same email, exactly one succeeds."""
        results: list[bool] = []

        def claim() -> None:
            # Each thread gets its own repository instance
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email("race@example.com", "$2b$10$hash", "1234")
            results.append(result)

        # Run 2 concurrent claims
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(claim) for _ in range(2)]
            for f in futures:
                f.result()

        # Exactly one should succeed
        assert results.count(True) == 1
        assert results.count(False) == 1

    def test_many_concurrent_claims_exactly_one_succeeds(self, pool: ConnectionPool) -> None:
        """When many concurrent claims for same email, exactly one succeeds."""
        results: list[bool] = []

        def claim() -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email("manyrace@example.com", "$2b$10$hash", "1234")
            results.append(result)

        # Run 10 concurrent claims
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(claim) for _ in range(10)]
            for f in futures:
                f.result()

        # Exactly one should succeed
        assert results.count(True) == 1
        assert results.count(False) == 9


class TestParameterizedQueries:
    """Tests verifying parameterized queries prevent SQL injection."""

    def test_email_with_special_characters(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """Email with SQL-like characters is handled safely."""
        # This would cause SQL injection if not parameterized
        malicious_email = "user'; DROP TABLE registrations; --@example.com"

        # Should handle gracefully (valid email format aside)
        result = repository.claim_email(malicious_email, "$2b$10$hash", "1234")
        assert result is True

    def test_password_hash_with_special_characters(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Password hash with special characters is stored correctly."""
        special_hash = "$2b$10$hash'with\"special;chars"
        repository.claim_email("special@example.com", special_hash, "1234")

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                ("special@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == special_hash


class TestVerifyAndActivateSuccess:
    """Tests for successful verify_and_activate scenarios."""

    def test_verify_and_activate_valid_credentials_returns_success(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Valid code and password returns SUCCESS and activates account."""
        email = "success@example.com"
        password = "correctpassword"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create CLAIMED registration
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.SUCCESS

    def test_activated_at_is_set_on_success(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Successful activation sets activated_at timestamp."""
        email = "timestamp@example.com"
        password = "password123"
        code = "5678"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        repository.verify_and_activate(email, code, password)

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT activated_at FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] is not None  # activated_at should be set

    def test_state_transitions_to_active_on_success(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Successful activation transitions state to ACTIVE."""
        email = "active@example.com"
        password = "password123"
        code = "9999"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        repository.verify_and_activate(email, code, password)

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE"


class TestVerifyAndActivateInvalidCode:
    """Tests for invalid code scenarios."""

    def test_wrong_code_returns_invalid_code(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Wrong verification code returns INVALID_CODE."""
        email = "wrongcode@example.com"
        password = "password123"
        correct_code = "1234"
        wrong_code = "9999"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, correct_code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, wrong_code, password)
        assert result == VerifyResult.INVALID_CODE

    def test_wrong_password_returns_invalid_code(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Wrong password returns INVALID_CODE (same as wrong code for security)."""
        email = "wrongpwd@example.com"
        correct_password = "correctpassword"
        wrong_password = "wrongpassword"
        code = "1234"
        password_hash = bcrypt.hashpw(correct_password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, wrong_password)
        assert result == VerifyResult.INVALID_CODE


class TestVerifyAndActivateAttemptCounting:
    """Tests for attempt counting and lockout."""

    def test_attempt_count_increments_on_failure(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Failed verification increments attempt_count."""
        email = "attempts@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # First failed attempt
        repository.verify_and_activate(email, "0000", password)

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == 1

    def test_state_transitions_to_locked_after_3_failures(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Account transitions to LOCKED after 3 failed attempts."""
        email = "lockout@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Three failed attempts
        repository.verify_and_activate(email, "0000", password)  # Attempt 1
        repository.verify_and_activate(email, "0000", password)  # Attempt 2
        result = repository.verify_and_activate(email, "0000", password)  # Attempt 3

        assert result == VerifyResult.LOCKED

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "LOCKED"
        assert row[1] == 3

    def test_locked_account_returns_locked(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Already locked account returns LOCKED even with correct credentials."""
        email = "alreadylocked@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create already LOCKED registration with 3 attempts
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, attempt_count)
                   VALUES (%s, %s, %s, 'LOCKED', 3)""",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.LOCKED

    def test_password_hash_purged_on_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Password hash is NULLed when account is locked (Data Stewardship)."""
        email = "purge@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Three failed attempts to trigger lockout
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] is None  # password_hash should be purged


class TestVerifyAndActivateNotFound:
    """Tests for not found scenarios."""

    def test_nonexistent_email_returns_not_found(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """Non-existent email returns NOT_FOUND."""
        result = repository.verify_and_activate("nonexistent@example.com", "1234", "password")
        assert result == VerifyResult.NOT_FOUND

    def test_active_account_returns_not_found(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Already ACTIVE account returns NOT_FOUND (not in CLAIMED state)."""
        email = "alreadyactive@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create already ACTIVE registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, activated_at)
                   VALUES (%s, %s, %s, 'ACTIVE', NOW())""",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.NOT_FOUND


class TestVerifyAndActivateExpired:
    """Tests for TTL expiration scenarios."""

    def test_expired_registration_returns_expired(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Registration older than 60 seconds returns EXPIRED."""
        email = "expired@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create registration with created_at 61 seconds ago
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '61 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.EXPIRED

    def test_registration_at_59_seconds_still_valid(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Registration at 59 seconds is still valid (within 60 second TTL)."""
        email = "stillvalid@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create registration with created_at 59 seconds ago
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '59 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.SUCCESS

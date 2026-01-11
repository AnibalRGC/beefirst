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

    def test_attempt_count_progression_0_to_3(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Attempt count progresses 0→1→2→3 with each failure (FR19).

        AC5: Verify each intermediate state is verifiable in the database.
        """
        email = "progression@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Verify initial state: attempt_count=0
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 0, "Initial attempt_count should be 0"
        assert row[1] == "CLAIMED", "Initial state should be CLAIMED"

        # Attempt 1: wrong code
        result1 = repository.verify_and_activate(email, "0000", password)
        assert result1 == VerifyResult.INVALID_CODE

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 1, "After 1st failure, attempt_count should be 1"
        assert row[1] == "CLAIMED", "After 1st failure, state should still be CLAIMED"

        # Attempt 2: wrong code
        result2 = repository.verify_and_activate(email, "0000", password)
        assert result2 == VerifyResult.INVALID_CODE

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 2, "After 2nd failure, attempt_count should be 2"
        assert row[1] == "CLAIMED", "After 2nd failure, state should still be CLAIMED"

        # Attempt 3: triggers lockout
        result3 = repository.verify_and_activate(email, "0000", password)
        assert result3 == VerifyResult.LOCKED

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 3, "After 3rd failure, attempt_count should be 3"
        assert row[1] == "LOCKED", "After 3rd failure, state should be LOCKED"

    def test_wrong_password_increments_attempt_count(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Wrong password (with correct code) also increments attempt_count (FR19).

        AC1: Both wrong code AND wrong password increment the counter.
        """
        email = "wrongpwd@example.com"
        password = "password123"
        code = "1234"
        wrong_password = "wrongpassword"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Attempt with correct code but wrong password
        result = repository.verify_and_activate(email, code, wrong_password)
        assert result == VerifyResult.INVALID_CODE  # Same result for both failures

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 1, "Wrong password should increment attempt_count"

    def test_mixed_failures_contribute_to_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Both wrong code and wrong password failures contribute to lockout.

        AC1: Verifies mixed failure types all count toward the 3-attempt lockout.
        """
        email = "mixedfailures@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Failure 1: wrong code
        repository.verify_and_activate(email, "0000", password)
        # Failure 2: wrong password (correct code)
        repository.verify_and_activate(email, code, "wrongpassword")
        # Failure 3: wrong code again - should trigger lockout
        result = repository.verify_and_activate(email, "0000", password)

        assert result == VerifyResult.LOCKED
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == "LOCKED"
        assert row[1] == 3

    def test_locked_account_fails_with_correct_credentials(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Locked account returns LOCKED even with correct code AND password.

        AC4: The locked state persists permanently.
        This is different from test_locked_account_returns_locked which uses
        a pre-locked account - this one locks through actual failures.
        """
        email = "lockedcorrect@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Lock the account through 3 failures
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)
        lock_result = repository.verify_and_activate(email, "0000", password)
        assert lock_result == VerifyResult.LOCKED

        # Now try with CORRECT code and password
        correct_result = repository.verify_and_activate(email, code, password)
        assert correct_result == VerifyResult.LOCKED, (
            "Locked state should persist even with correct credentials"
        )


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
        """Registration older than 60 seconds returns EXPIRED and transitions state."""
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

        # AC2: Verify database state actually transitioned to EXPIRED
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "EXPIRED", "State should transition to EXPIRED"
        # AC3: Verify password_hash is purged (Data Stewardship)
        assert row[1] is None, "Password hash should be NULL after expiration"

    def test_registration_at_59_seconds_still_valid(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Registration at 59 seconds is still valid (within 60 second TTL).

        Boundary condition: TTL check uses `created_at > NOW() - INTERVAL '60 seconds'`
        At 59 seconds, the registration is within the window and should succeed.
        """
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

    def test_password_hash_purged_on_expiration(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Password hash is NULLed when registration expires (Data Stewardship).

        FR24: System can purge hashed passwords when registrations expire
        FR25: No ghost credentials for expired accounts
        NFR-S6: Purge within 60 seconds of expiration
        """
        email = "purge@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create expired registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '61 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        # Verify password_hash is set BEFORE expiration check
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] is not None, "Password hash should exist before expiration"

        # Trigger expiration check
        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.EXPIRED

        # Verify password_hash is NULL AFTER expiration
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] is None, "Password hash should be purged after expiration"

    def test_already_expired_returns_not_found(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Already EXPIRED registration returns NOT_FOUND.

        AC6: Consistent with other non-CLAIMED states (ACTIVE, LOCKED)
        An EXPIRED registration should not be re-expirable.
        """
        email = "alreadyexpired@example.com"
        password = "password123"
        code = "1234"

        # Insert directly with EXPIRED state (no password_hash per Data Stewardship)
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations
                   (email, password_hash, verification_code, state, created_at)
                   VALUES (%s, NULL, %s, 'EXPIRED', NOW() - INTERVAL '120 seconds')""",
                (email, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.NOT_FOUND


class TestDataStewardship:
    """Data Stewardship tests for FR24, FR25, NFR-S5, NFR-S6.

    These tests verify the Data Stewardship principle:
    - FR24: Purge hashed passwords when registrations expire or lock
    - FR25: No "ghost credentials" for unverified accounts
    - NFR-S5: Database credentials never appear in application logs
    - NFR-S6: Hashed passwords purged within 60 seconds of expiration

    Ghost credentials are password hashes that exist for accounts that:
    - Cannot be activated (EXPIRED, LOCKED states)
    - Were never fully verified
    """

    def test_expired_state_has_null_password_hash(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """EXPIRED registrations have password_hash = NULL (FR24, FR25).

        After a registration expires, no ghost credentials should exist.
        """
        email = "ds_expired@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create expired registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '61 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        # Trigger expiration (lazy transition)
        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.EXPIRED

        # Verify: EXPIRED state must have NULL password_hash
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "EXPIRED", "State should be EXPIRED"
        assert row[1] is None, "EXPIRED state must have NULL password_hash (FR24, FR25)"

    def test_locked_state_has_null_password_hash(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """LOCKED registrations have password_hash = NULL (FR24, FR25).

        After an account is locked, no ghost credentials should exist.
        """
        email = "ds_locked@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create registration
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # Lock the account through 3 failures
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)
        result = repository.verify_and_activate(email, "0000", password)
        assert result == VerifyResult.LOCKED

        # Verify: LOCKED state must have NULL password_hash
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "LOCKED", "State should be LOCKED"
        assert row[1] is None, "LOCKED state must have NULL password_hash (FR24, FR25)"

    def test_claimed_state_has_password_hash(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """CLAIMED registrations retain password_hash (positive test).

        Fresh registrations in CLAIMED state should have their password hash
        for verification purposes.
        """
        email = "ds_claimed@example.com"
        password_hash = "$2b$10$validhashvalue"
        code = "1234"

        # Create fresh registration
        repository.claim_email(email, password_hash, code)

        # Verify: CLAIMED state must have password_hash
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "CLAIMED", "State should be CLAIMED"
        assert row[1] is not None, "CLAIMED state must have password_hash"
        assert row[1] == password_hash, "Password hash should be stored correctly"

    def test_no_ghost_credentials_after_expiration(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """No ghost credentials exist after expiration (FR25).

        Explicitly verifies that password_hash transitions from non-NULL to NULL
        during the expiration process.
        """
        email = "ghost_expire@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create registration with password hash
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '61 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        # BEFORE: Verify password_hash exists
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] is not None, "Password hash should exist before expiration"

        # Trigger expiration
        repository.verify_and_activate(email, code, password)

        # AFTER: Verify no ghost credentials (password_hash is NULL)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] is None, "No ghost credentials should exist after expiration (FR25)"

    def test_no_ghost_credentials_after_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """No ghost credentials exist after lockout (FR25).

        Explicitly verifies that password_hash transitions from non-NULL to NULL
        during the lockout process.
        """
        email = "ghost_lock@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create registration with password hash
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        # BEFORE: Verify password_hash exists
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] is not None, "Password hash should exist before lockout"

        # Trigger lockout
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)
        repository.verify_and_activate(email, "0000", password)

        # AFTER: Verify no ghost credentials (password_hash is NULL)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] is None, "No ghost credentials should exist after lockout (FR25)"

    def test_active_state_may_have_password_hash(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """ACTIVE registrations may retain password_hash.

        Unlike EXPIRED and LOCKED, ACTIVE accounts may keep their password hash
        for potential future login verification (if implemented).
        """
        email = "ds_active@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create and activate registration
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                (email, password_hash, code),
            )
            conn.commit()

        result = repository.verify_and_activate(email, code, password)
        assert result == VerifyResult.SUCCESS

        # Verify: ACTIVE state may have password_hash (not purged)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE", "State should be ACTIVE"
        # Note: ACTIVE accounts may or may not retain password_hash
        # The current implementation retains it, but this is acceptable
        # as ACTIVE is a terminal successful state

    def test_credential_purge_is_atomic_with_state_transition(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Credential purge happens atomically with state transition (FR24, FR25).

        The UPDATE that changes state also sets password_hash = NULL in the same
        SQL statement, ensuring atomicity.
        """
        email = "atomic_purge@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Create expired registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, created_at)
                   VALUES (%s, %s, %s, NOW() - INTERVAL '61 seconds')""",
                (email, password_hash, code),
            )
            conn.commit()

        # Trigger expiration
        repository.verify_and_activate(email, code, password)

        # Verify both state and password_hash changed together
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        # If state is EXPIRED, password_hash MUST be NULL (atomic)
        assert row[0] == "EXPIRED", "State should be EXPIRED"
        assert row[1] is None, "If state=EXPIRED, password_hash must be NULL (atomic purge)"


class TestEmailRelease:
    """Email release and re-registration tests - FR17, FR26.

    These tests verify that emails in EXPIRED or LOCKED states can be
    re-registered, while ACTIVE and CLAIMED states cannot.

    - FR17: Release emails from EXPIRED/LOCKED states for re-registration
    - FR26: Timestamp state transitions using database time
    - FR18: Prevent race conditions (atomic SQL operations)
    """

    def test_claim_email_succeeds_for_expired_email(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration succeeds for EXPIRED emails (FR17).

        AC1: Re-registration succeeds for EXPIRED emails with fresh data.
        """
        email = "reregister_expired@example.com"

        # Create EXPIRED registration (with NULL password_hash per Data Stewardship)
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state)
                   VALUES (%s, NULL, '0000', 'EXPIRED')""",
                (email,),
            )
            conn.commit()

        # Re-register
        result = repository.claim_email(email, "$2b$10$newhash", "9999")
        assert result is True, "Re-registration should succeed for EXPIRED email"

        # Verify record was reset
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, verification_code, attempt_count, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED", "State should reset to CLAIMED"
        assert row[1] == "9999", "New verification code should be stored"
        assert row[2] == 0, "Attempt count should reset to 0"
        assert row[3] is not None, "New password hash should be stored"

    def test_claim_email_succeeds_for_locked_email(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration succeeds for LOCKED emails (FR17).

        AC2: Re-registration succeeds for LOCKED emails with fresh data.
        """
        email = "reregister_locked@example.com"

        # Create LOCKED registration (with NULL password_hash per Data Stewardship)
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, attempt_count)
                   VALUES (%s, NULL, '0000', 'LOCKED', 3)""",
                (email,),
            )
            conn.commit()

        # Re-register
        result = repository.claim_email(email, "$2b$10$newhash", "8888")
        assert result is True, "Re-registration should succeed for LOCKED email"

        # Verify record was reset
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, verification_code, attempt_count, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED", "State should reset to CLAIMED"
        assert row[1] == "8888", "New verification code should be stored"
        assert row[2] == 0, "Attempt count should reset to 0"
        assert row[3] is not None, "New password hash should be stored"

    def test_claim_email_fails_for_active_email(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration fails for ACTIVE emails.

        AC3: ACTIVE accounts cannot be re-registered.
        """
        email = "active_email@example.com"

        # Create ACTIVE registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, activated_at)
                   VALUES (%s, '$2b$10$activehash', '1234', 'ACTIVE', NOW())""",
                (email,),
            )
            conn.commit()

        # Attempt re-registration
        result = repository.claim_email(email, "$2b$10$newhash", "5678")
        assert result is False, "Re-registration should fail for ACTIVE email"

        # Verify ACTIVE record was NOT modified
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, verification_code, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "ACTIVE", "State should remain ACTIVE"
        assert row[1] == "1234", "Original verification code should remain"
        assert row[2] == "$2b$10$activehash", "Original password hash should remain"

    def test_claim_email_fails_for_claimed_email(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration fails for CLAIMED emails (in-progress registration).

        AC4: CLAIMED emails cannot be re-registered - let them expire naturally.
        """
        email = "claimed_email@example.com"

        # Create CLAIMED registration (in-progress)
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state)
                   VALUES (%s, '$2b$10$claimedhash', '1234', 'CLAIMED')""",
                (email,),
            )
            conn.commit()

        # Attempt re-registration
        result = repository.claim_email(email, "$2b$10$newhash", "5678")
        assert result is False, "Re-registration should fail for CLAIMED email"

        # Verify CLAIMED record was NOT modified
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, verification_code, password_hash FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED", "State should remain CLAIMED"
        assert row[1] == "1234", "Original verification code should remain"
        assert row[2] == "$2b$10$claimedhash", "Original password hash should remain"

    def test_created_at_updated_on_reregistration(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration updates created_at to new timestamp (FR26).

        AC1: New `created_at` timestamp is set using database time.
        """
        email = "timestamp_reregister@example.com"

        # Create EXPIRED registration with old timestamp
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, created_at)
                   VALUES (%s, NULL, '0000', 'EXPIRED', NOW() - INTERVAL '1 hour')""",
                (email,),
            )
            conn.commit()

        # Get original timestamp
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT created_at FROM registrations WHERE email = %s",
                (email,),
            )
            original_created_at = cursor.fetchone()[0]

        # Re-register
        result = repository.claim_email(email, "$2b$10$newhash", "9999")
        assert result is True

        # Verify created_at was updated
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT created_at FROM registrations WHERE email = %s",
                (email,),
            )
            new_created_at = cursor.fetchone()[0]

        assert new_created_at > original_created_at, (
            "created_at should be updated to new timestamp (FR26)"
        )

    def test_activated_at_cleared_on_reregistration(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """Re-registration clears activated_at timestamp.

        The re-registered account has not been activated yet.
        """
        email = "clear_activated@example.com"

        # Create EXPIRED registration (simulate account that was once active then expired)
        # Note: In practice, ACTIVE doesn't transition to EXPIRED, but test the field reset
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state, activated_at)
                   VALUES (%s, NULL, '0000', 'EXPIRED', NOW() - INTERVAL '1 hour')""",
                (email,),
            )
            conn.commit()

        # Re-register
        result = repository.claim_email(email, "$2b$10$newhash", "9999")
        assert result is True

        # Verify activated_at was cleared
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT activated_at FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] is None, "activated_at should be NULL after re-registration"

    def test_concurrent_reregistration_exactly_one_succeeds(self, pool: ConnectionPool) -> None:
        """Concurrent re-registration attempts - exactly one succeeds (FR18).

        AC5: Multiple concurrent re-registration attempts for the same EXPIRED email
        result in exactly one success, with no data corruption.
        """
        email = "concurrent_reregister@example.com"

        # Create EXPIRED registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state)
                   VALUES (%s, NULL, '0000', 'EXPIRED')""",
                (email,),
            )
            conn.commit()

        results: list[bool] = []

        def attempt_reregister(code: str) -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email(email, f"$2b$10$hash{code}", code)
            results.append(result)

        # Run 5 concurrent re-registration attempts
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attempt_reregister, str(i).zfill(4)) for i in range(5)]
            for f in futures:
                f.result()

        # Exactly one should succeed (first UPDATE wins, others see CLAIMED state)
        assert results.count(True) == 1, "Exactly one re-registration should succeed"
        assert results.count(False) == 4, "Other attempts should fail"

        # Verify no data corruption - record should be in consistent state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED", "Final state should be CLAIMED"
        assert row[1] == 0, "Attempt count should be 0"

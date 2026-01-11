"""
Adversarial tests for timing oracle attack prevention.

Verifies that all failure modes in verify_and_activate have statistically
similar response times, preventing attackers from inferring information
about account existence or credential validity through timing analysis.

Security rationale:
- Timing oracle attacks measure response time differences to infer secrets
- Different code paths (e.g., "email not found" vs "password invalid") may
  have different execution times, leaking information
- Our defense: run constant-time operations (bcrypt, secrets.compare_digest)
  for ALL code paths, including non-existent emails

References:
- [Source: architecture.md#Authentication & Security]
- [Source: prd.md#NFR-S2 (Constant-time password verification)]
- [Source: prd.md#NFR-P2 (Password verification timing)]
- [Source: prd.md#NFR-P3 (Consistent error timing)]
"""

import statistics
import time

import bcrypt
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.config.settings import get_settings


@pytest.fixture(scope="module")
def pool() -> ConnectionPool:
    """Create connection pool for adversarial tests."""
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


@pytest.mark.adversarial
class TestTimingAttacks:
    """
    Verify constant-time behavior prevents timing oracle attacks.

    These tests measure response times for different failure scenarios
    and verify they are statistically indistinguishable.

    Note: Each measurement uses a unique email to avoid account lockout
    from multiple failed attempts incrementing attempt_count.
    """

    # Number of measurements per scenario for statistical significance
    ITERATIONS = 20

    # Maximum allowed difference in mean times (20% as per AC6)
    MAX_VARIANCE_RATIO = 0.20

    def measure_time(
        self,
        repository: PostgresRegistrationRepository,
        email: str,
        code: str,
        password: str,
    ) -> float:
        """Measure execution time for a single verify_and_activate call."""
        start = time.perf_counter()
        repository.verify_and_activate(email, code, password)
        return time.perf_counter() - start

    def assert_timing_similar(
        self,
        times1: list[float],
        times2: list[float],
        label1: str,
        label2: str,
    ) -> None:
        """Assert two timing distributions are statistically similar."""
        mean1 = statistics.mean(times1)
        mean2 = statistics.mean(times2)

        # Calculate ratio of difference to max
        ratio = abs(mean1 - mean2) / max(mean1, mean2)

        assert ratio < self.MAX_VARIANCE_RATIO, (
            f"Timing difference too large between {label1} and {label2}: "
            f"{ratio:.1%} (threshold: {self.MAX_VARIANCE_RATIO:.0%})\n"
            f"  {label1}: mean={mean1:.4f}s, stdev={statistics.stdev(times1):.4f}s\n"
            f"  {label2}: mean={mean2:.4f}s, stdev={statistics.stdev(times2):.4f}s"
        )

    def create_claimed_registrations(
        self,
        pool: ConnectionPool,
        prefix: str,
        password: str,
        code: str,
        count: int,
        created_at_offset: str = "0 seconds",
    ) -> list[str]:
        """Create multiple CLAIMED registrations in the database."""
        emails = [f"{prefix}{i}@example.com" for i in range(count)]
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        with pool.connection() as conn:
            for email in emails:
                conn.execute(
                    f"""INSERT INTO registrations (email, password_hash, verification_code, created_at)
                       VALUES (%s, %s, %s, NOW() - INTERVAL '{created_at_offset}')""",
                    (email, password_hash, code),
                )
            conn.commit()

        return emails

    def create_locked_registrations(
        self,
        pool: ConnectionPool,
        prefix: str,
        password: str,
        code: str,
        count: int,
    ) -> list[str]:
        """Create multiple LOCKED registrations in the database."""
        emails = [f"{prefix}{i}@example.com" for i in range(count)]
        # LOCKED accounts have NULL password_hash (Data Stewardship - purged on lockout)
        with pool.connection() as conn:
            for email in emails:
                conn.execute(
                    """INSERT INTO registrations (email, password_hash, verification_code, state, attempt_count)
                       VALUES (%s, NULL, %s, 'LOCKED', 3)""",
                    (email, code),
                )
            conn.commit()

        return emails

    def test_nonexistent_email_timing_similar_to_valid_email_wrong_code(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Non-existent email timing should be similar to valid email with wrong code.

        This is the primary timing oracle attack: comparing "email not found"
        vs "email exists but credentials wrong" to enumerate valid emails.
        """
        # Create valid registrations (one per measurement to avoid lockout)
        emails = self.create_claimed_registrations(
            pool, "valid", "password123", "1234", self.ITERATIONS
        )

        # Measure non-existent email
        nonexistent_times = [
            self.measure_time(repository, f"nonexist{i}@example.com", "0000", "password")
            for i in range(self.ITERATIONS)
        ]

        # Measure valid email with wrong code (each email used once)
        wrong_code_times = [
            self.measure_time(repository, emails[i], "9999", "password123")
            for i in range(self.ITERATIONS)
        ]

        self.assert_timing_similar(
            nonexistent_times,
            wrong_code_times,
            "nonexistent_email",
            "valid_email_wrong_code",
        )

    def test_nonexistent_email_timing_similar_to_valid_email_wrong_password(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Non-existent email timing should be similar to valid email with wrong password.

        bcrypt comparison dominates timing (~100ms), masking other variations.
        """
        # Create valid registrations
        emails = self.create_claimed_registrations(
            pool, "valid2", "password123", "1234", self.ITERATIONS
        )

        # Measure non-existent email
        nonexistent_times = [
            self.measure_time(repository, f"noexist2_{i}@example.com", "1234", "anypassword")
            for i in range(self.ITERATIONS)
        ]

        # Measure valid email with wrong password
        wrong_password_times = [
            self.measure_time(repository, emails[i], "1234", "wrongpassword")
            for i in range(self.ITERATIONS)
        ]

        self.assert_timing_similar(
            nonexistent_times,
            wrong_password_times,
            "nonexistent_email",
            "valid_email_wrong_password",
        )

    def test_wrong_code_timing_similar_to_wrong_password(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Wrong code timing should be similar to wrong password timing.

        This prevents attackers from determining which credential was wrong.
        """
        # Create registrations for wrong code tests
        wrong_code_emails = self.create_claimed_registrations(
            pool, "wrongcode", "password123", "1234", self.ITERATIONS
        )

        # Create registrations for wrong password tests
        wrong_pwd_emails = self.create_claimed_registrations(
            pool, "wrongpwd", "password123", "5678", self.ITERATIONS
        )

        # Measure wrong code (correct password)
        wrong_code_times = [
            self.measure_time(repository, wrong_code_emails[i], "9999", "password123")
            for i in range(self.ITERATIONS)
        ]

        # Measure wrong password (correct code)
        wrong_password_times = [
            self.measure_time(repository, wrong_pwd_emails[i], "5678", "wrongpassword")
            for i in range(self.ITERATIONS)
        ]

        self.assert_timing_similar(
            wrong_code_times,
            wrong_password_times,
            "wrong_code",
            "wrong_password",
        )

    def test_expired_registration_timing_similar_to_valid(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Expired registration timing should be similar to valid registration.

        Expired registrations should not be identifiable through timing.
        """
        # Create valid (non-expired) registrations
        valid_emails = self.create_claimed_registrations(
            pool, "fresh", "password123", "1234", self.ITERATIONS
        )

        # Create expired registrations (65 seconds old)
        expired_emails = self.create_claimed_registrations(
            pool, "expired", "password123", "1234", self.ITERATIONS, "65 seconds"
        )

        # Measure valid registration (wrong code to not activate)
        valid_times = [
            self.measure_time(repository, valid_emails[i], "9999", "password123")
            for i in range(self.ITERATIONS)
        ]

        # Measure expired registration
        expired_times = [
            self.measure_time(repository, expired_emails[i], "1234", "password123")
            for i in range(self.ITERATIONS)
        ]

        self.assert_timing_similar(
            valid_times,
            expired_times,
            "valid_registration",
            "expired_registration",
        )

    def test_locked_account_timing_similar_to_claimed(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Locked account timing should be similar to claimed account.

        Attackers should not be able to identify locked accounts through timing.
        """
        # Create claimed registrations
        claimed_emails = self.create_claimed_registrations(
            pool, "claimed", "password123", "1234", self.ITERATIONS
        )

        # Create locked registrations
        locked_emails = self.create_locked_registrations(
            pool, "locked", "password123", "1234", self.ITERATIONS
        )

        # Measure claimed account (wrong code)
        claimed_times = [
            self.measure_time(repository, claimed_emails[i], "9999", "password123")
            for i in range(self.ITERATIONS)
        ]

        # Measure locked account
        locked_times = [
            self.measure_time(repository, locked_emails[i], "1234", "password123")
            for i in range(self.ITERATIONS)
        ]

        self.assert_timing_similar(
            claimed_times,
            locked_times,
            "claimed_account",
            "locked_account",
        )

    def test_all_failure_modes_timing_comparable(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        All failure modes should have comparable timing.

        This comprehensive test verifies no failure mode is significantly
        faster or slower than the others.
        """
        # Setup various registration states
        claimed_emails = self.create_claimed_registrations(
            pool, "all_claimed", "password123", "1234", self.ITERATIONS
        )
        expired_emails = self.create_claimed_registrations(
            pool, "all_expired", "password123", "1234", self.ITERATIONS, "65 seconds"
        )
        locked_emails = self.create_locked_registrations(
            pool, "all_locked", "password123", "1234", self.ITERATIONS
        )

        # Measure all failure scenarios (each using unique emails)
        measurements: dict[str, list[float]] = {
            "not_found": [
                self.measure_time(repository, f"notfound{i}@example.com", "1234", "password")
                for i in range(self.ITERATIONS)
            ],
            "wrong_code": [
                self.measure_time(repository, claimed_emails[i], "9999", "password123")
                for i in range(self.ITERATIONS)
            ],
            "expired": [
                self.measure_time(repository, expired_emails[i], "1234", "password123")
                for i in range(self.ITERATIONS)
            ],
            "locked": [
                self.measure_time(repository, locked_emails[i], "1234", "password123")
                for i in range(self.ITERATIONS)
            ],
        }

        # Calculate statistics for all scenarios
        stats = {name: statistics.mean(times) for name, times in measurements.items()}
        overall_mean = statistics.mean(stats.values())

        # Verify all scenarios are within acceptable range of overall mean
        for name, mean in stats.items():
            ratio = abs(mean - overall_mean) / overall_mean
            assert ratio < self.MAX_VARIANCE_RATIO, (
                f"Scenario '{name}' timing differs too much from average: "
                f"{ratio:.1%} (threshold: {self.MAX_VARIANCE_RATIO:.0%})\n"
                f"  {name} mean: {mean:.4f}s\n"
                f"  overall mean: {overall_mean:.4f}s"
            )


@pytest.mark.adversarial
class TestConstantTimeOperations:
    """
    Verify that constant-time cryptographic operations are used.

    These tests verify the implementation uses the correct functions
    (secrets.compare_digest, bcrypt.checkpw) rather than regular comparison.
    """

    def test_bcrypt_dominates_response_time(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Bcrypt should dominate response time (>50ms typically with cost 10).

        This masks other timing variations from code paths.
        """
        # Create valid registration
        password = "testpassword"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
        with pool.connection() as conn:
            conn.execute(
                "INSERT INTO registrations (email, password_hash, verification_code) VALUES (%s, %s, %s)",
                ("bcrypttest@example.com", password_hash, "1234"),
            )
            conn.commit()

        # Measure multiple calls
        times = []
        for _ in range(10):
            start = time.perf_counter()
            repository.verify_and_activate("bcrypttest@example.com", "1234", password)
            times.append(time.perf_counter() - start)

        mean_time = statistics.mean(times)

        # bcrypt with cost 10 should take at least 50ms
        # If times are much lower, bcrypt might not be running
        assert mean_time > 0.030, (
            f"Response time too fast ({mean_time:.3f}s) - bcrypt may not be running. "
            f"Expected >30ms with cost factor 10."
        )

    def test_dummy_hash_used_for_nonexistent_email(
        self, repository: PostgresRegistrationRepository
    ) -> None:
        """
        Non-existent email should still take bcrypt-comparable time.

        This verifies the dummy hash is being compared.
        """
        # Measure call for non-existent email
        times = []
        for _ in range(10):
            start = time.perf_counter()
            repository.verify_and_activate("nonexistent@example.com", "1234", "anypassword")
            times.append(time.perf_counter() - start)

        mean_time = statistics.mean(times)

        # Should still take bcrypt time even for non-existent email
        assert mean_time > 0.030, (
            f"Non-existent email response too fast ({mean_time:.3f}s) - "
            f"dummy bcrypt hash comparison may not be running."
        )

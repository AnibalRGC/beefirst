"""
Adversarial tests for brute force attack prevention.

Verifies that the 3-strike lockout mechanism effectively prevents
brute force attacks against account activation, protecting users
from credential guessing attacks.

Security rationale:
- Brute force attacks try many code/password combinations rapidly
- Without rate limiting, attacker could try all 10000 4-digit codes
- 3-strike lockout makes brute force infeasible (3/10000 = 0.03% success rate)
- Locked accounts cannot be activated even with correct credentials

References:
- [Source: architecture.md#Trust State Machine]
- [Source: prd.md#FR16 (CLAIMED->LOCKED after 3 failures)]
- [Source: prd.md#FR19 (Increment attempt_count on failure)]
- [Source: prd.md#FR20 (Lock after threshold)]
"""

import bcrypt
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.config.settings import get_settings
from src.domain.ports import VerifyResult


@pytest.fixture(scope="module")
def pool() -> ConnectionPool:
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
def clean_database(pool: ConnectionPool) -> None:
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


@pytest.mark.adversarial
class TestBruteForceAttacks:
    """
    Adversarial tests simulating brute force code guessing attacks.

    These tests verify that an attacker attempting to guess verification
    codes is locked out after 3 failed attempts.
    """

    def test_code_brute_force_triggers_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Simulate attacker brute forcing verification codes.

        Attack scenario: Attacker knows the email but not the code,
        and attempts to guess the 4-digit code.

        Expected defense: Account locks after 3 incorrect guesses.
        """
        email = "victim@example.com"
        password = "victimpassword"
        correct_code = "7890"

        create_registration(pool, email, password, correct_code)

        # Attacker guesses wrong codes
        wrong_codes = ["0000", "1111", "2222"]
        results = []

        for guess in wrong_codes:
            result = repository.verify_and_activate(email, guess, password)
            results.append(result)

        # First two should be INVALID_CODE, third should be LOCKED
        assert results[0] == VerifyResult.INVALID_CODE
        assert results[1] == VerifyResult.INVALID_CODE
        assert results[2] == VerifyResult.LOCKED

        # Verify account is LOCKED in database
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "LOCKED", "Account should be LOCKED after 3 failures"
        assert row[1] == 3, "Attempt count should be 3"

    def test_password_brute_force_triggers_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Simulate attacker brute forcing passwords.

        Attack scenario: Attacker has the correct code but guesses passwords.

        Expected defense: Account locks after 3 incorrect password attempts.
        """
        email = "pwdvictim@example.com"
        correct_password = "correctpassword123"
        correct_code = "5678"

        create_registration(pool, email, correct_password, correct_code)

        # Attacker guesses wrong passwords with correct code
        wrong_passwords = ["password1", "password2", "password3"]
        results = []

        for guess in wrong_passwords:
            result = repository.verify_and_activate(email, correct_code, guess)
            results.append(result)

        # All should fail, third should lock
        assert results[2] == VerifyResult.LOCKED

        # Verify lockout
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s", (email,)
            )
            row = cursor.fetchone()

        assert row[0] == "LOCKED"

    def test_mixed_failures_contribute_to_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify mixed failure types all count toward lockout.

        Attack scenario: Attacker tries different attack vectors -
        sometimes wrong code, sometimes wrong password.

        Expected defense: All failure types increment attempt counter.
        """
        email = "mixedattack@example.com"
        password = "realpassword"
        code = "1234"

        create_registration(pool, email, password, code)

        # Attacker uses mixed attack strategy
        attacks = [
            ("0000", password),      # Wrong code
            (code, "wrongpwd"),      # Wrong password
            ("9999", "wrongpwd"),    # Wrong both
        ]

        results = []
        for attack_code, attack_password in attacks:
            result = repository.verify_and_activate(email, attack_code, attack_password)
            results.append(result)

        assert results[2] == VerifyResult.LOCKED, (
            "Mixed attack types should all count toward lockout"
        )

    def test_locked_account_stays_locked_with_correct_credentials(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify locked account cannot be recovered with correct credentials.

        Attack scenario: After locking account through failed attempts,
        attacker finally guesses correct credentials.

        Expected defense: LOCKED state is permanent - correct credentials don't help.
        """
        email = "lockedforever@example.com"
        password = "correctpassword"
        code = "4321"

        create_registration(pool, email, password, code)

        # Lock account through failed attempts
        for _ in range(3):
            repository.verify_and_activate(email, "0000", password)

        # Now try with CORRECT credentials
        result = repository.verify_and_activate(email, code, password)

        assert result == VerifyResult.LOCKED, (
            "Locked account should remain locked even with correct credentials"
        )

    def test_rapid_sequential_attacks_all_counted(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify rapid sequential attacks are all properly counted.

        Attack scenario: Attacker sends requests as fast as possible
        hoping to bypass counting mechanism.

        Expected defense: All attempts are atomically counted.
        """
        email = "rapidattack@example.com"
        password = "password123"
        code = "9876"

        create_registration(pool, email, password, code)

        # Rapid-fire attacks (synchronous but as fast as possible)
        wrong_codes = [f"{i:04d}" for i in range(10)]  # 0000-0009
        results = []

        for guess in wrong_codes:
            result = repository.verify_and_activate(email, guess, password)
            results.append(result)

        # After 3 failures, all subsequent should return LOCKED
        assert results[2] == VerifyResult.LOCKED, "3rd attempt should trigger LOCKED"
        assert all(
            r == VerifyResult.LOCKED for r in results[3:]
        ), "All attempts after lockout should return LOCKED"


@pytest.mark.adversarial
class TestAttemptCountProgression:
    """
    Verify attempt count correctly progresses during attack.

    These tests verify the internal state machine transitions correctly
    as an attacker makes failed attempts.
    """

    def test_attempt_count_0_to_3_progression(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify complete progression: 0 -> 1 -> 2 -> 3 (locked).

        Each intermediate state should be verifiable in the database.
        """
        email = "progression@example.com"
        password = "password123"
        code = "1234"

        create_registration(pool, email, password, code)

        # Verify initial state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 0, "Initial attempt_count should be 0"
        assert row[1] == "CLAIMED", "Initial state should be CLAIMED"

        # Attack attempt 1
        result1 = repository.verify_and_activate(email, "0000", password)
        assert result1 == VerifyResult.INVALID_CODE

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 1, "After 1st attack, attempt_count should be 1"
        assert row[1] == "CLAIMED", "After 1st attack, state should still be CLAIMED"

        # Attack attempt 2
        result2 = repository.verify_and_activate(email, "1111", password)
        assert result2 == VerifyResult.INVALID_CODE

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 2, "After 2nd attack, attempt_count should be 2"
        assert row[1] == "CLAIMED", "After 2nd attack, state should still be CLAIMED"

        # Attack attempt 3 - triggers lockout
        result3 = repository.verify_and_activate(email, "2222", password)
        assert result3 == VerifyResult.LOCKED

        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT attempt_count, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == 3, "After 3rd attack, attempt_count should be 3"
        assert row[1] == "LOCKED", "After 3rd attack, state should be LOCKED"


@pytest.mark.adversarial
class TestCredentialPurgeOnLockout:
    """
    Verify credentials are purged when account is locked (Data Stewardship).

    This prevents the locked account from being a security liability -
    the password hash is removed so it cannot be extracted.
    """

    def test_password_hash_purged_on_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify password_hash is NULL after lockout (FR24, FR25).

        Security rationale: Even if attacker gains database access,
        locked accounts don't contain usable password hashes.
        """
        email = "purgetest@example.com"
        password = "secretpassword"
        code = "5555"

        create_registration(pool, email, password, code)

        # Verify password_hash exists before lockout
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s", (email,)
            )
            row = cursor.fetchone()
        assert row[0] is not None, "Password hash should exist before lockout"
        assert row[0].startswith("$2b$"), "Should be bcrypt hash"

        # Trigger lockout
        for _ in range(3):
            repository.verify_and_activate(email, "0000", password)

        # Verify password_hash is purged
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash, state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] is None, "Password hash should be NULL after lockout (FR24)"
        assert row[1] == "LOCKED", "State should be LOCKED"

    def test_no_ghost_credentials_after_lockout(
        self, repository: PostgresRegistrationRepository, pool: ConnectionPool
    ) -> None:
        """
        Verify no ghost credentials exist for locked account (FR25).

        Ghost credentials are password hashes that exist for accounts
        that cannot be used (LOCKED state).
        """
        email = "noghost@example.com"
        password = "password123"
        code = "4444"

        create_registration(pool, email, password, code)

        # Lock the account
        for _ in range(3):
            repository.verify_and_activate(email, "0000", password)

        # Verify: LOCKED account should not have password_hash (ghost credential)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s AND state = 'LOCKED'",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None, "LOCKED registration should exist"
        assert row[0] is None, "No ghost credentials: LOCKED accounts must have NULL password_hash"

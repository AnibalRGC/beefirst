"""
Adversarial tests for race condition attack prevention.

Verifies that concurrent operations on the same email are handled atomically,
preventing attackers from exploiting race conditions to:
- Create duplicate accounts
- Bypass registration restrictions
- Corrupt data through concurrent modifications

Security rationale:
- Race conditions can allow attackers to register the same email multiple times
- Concurrent re-registration attacks could corrupt registration state
- Atomic SQL operations (ON CONFLICT, SELECT FOR UPDATE) prevent these attacks

References:
- [Source: architecture.md#Data Architecture]
- [Source: prd.md#FR18 (Prevent race conditions)]
"""

import threading
from concurrent.futures import ThreadPoolExecutor

import bcrypt
import pytest
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.domain.ports import VerifyResult

# Apply adversarial marker to all tests in this module
pytestmark = pytest.mark.adversarial


class TestRaceConditionAttacks:
    """
    Adversarial tests simulating race condition attacks.

    These tests simulate an attacker rapidly attempting concurrent
    registrations to exploit potential race conditions in the system.
    """

    def test_concurrent_registration_attack_exactly_one_succeeds(
        self, pool: ConnectionPool
    ) -> None:
        """
        Simulate attacker attempting concurrent registrations for same email.

        Attack scenario: Attacker rapidly submits multiple registration requests
        simultaneously hoping to register the same email multiple times.

        Expected defense: ON CONFLICT clause ensures atomic claim - exactly one
        registration succeeds, all others fail gracefully.
        """
        email = "attack@example.com"
        results: list[bool] = []
        results_lock = threading.Lock()
        num_attackers = 5  # Simulate 5 concurrent attack requests

        def attack_register() -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email(email, "$2b$10$attackhash", "1234")
            with results_lock:
                results.append(result)

        # Launch concurrent attack
        with ThreadPoolExecutor(max_workers=num_attackers) as executor:
            futures = [executor.submit(attack_register) for _ in range(num_attackers)]
            for f in futures:
                f.result()

        # Defense verification: exactly one should succeed
        assert results.count(True) == 1, (
            f"Race condition vulnerability: {results.count(True)} registrations succeeded "
            f"(expected exactly 1)"
        )
        assert results.count(False) == num_attackers - 1

        # Verify database integrity: only one record exists
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM registrations WHERE email = %s", (email,)
            )
            count = cursor.fetchone()[0]
        assert count == 1, f"Data corruption: {count} records for same email (expected 1)"

    def test_high_volume_concurrent_registration_attack(
        self, pool: ConnectionPool
    ) -> None:
        """
        Simulate high-volume concurrent registration attack.

        Attack scenario: DDoS-style attack with many concurrent registration
        attempts for the same email, testing system resilience under load.

        Expected defense: System remains consistent under high concurrency.
        """
        email = "ddos@example.com"
        results: list[bool] = []
        results_lock = threading.Lock()
        num_attackers = 20  # Higher concurrency attack

        def attack_register() -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email(email, "$2b$10$attackhash", "1234")
            with results_lock:
                results.append(result)

        # Launch high-volume attack
        with ThreadPoolExecutor(max_workers=num_attackers) as executor:
            futures = [executor.submit(attack_register) for _ in range(num_attackers)]
            for f in futures:
                f.result()

        # Defense verification
        assert results.count(True) == 1, (
            f"High-volume race attack succeeded: {results.count(True)} registrations "
            f"(expected exactly 1)"
        )

    def test_concurrent_reregistration_attack(self, pool: ConnectionPool) -> None:
        """
        Simulate attack attempting concurrent re-registrations of EXPIRED email.

        Attack scenario: Attacker detects an EXPIRED registration and attempts
        multiple concurrent re-registrations to exploit potential race conditions.

        Expected defense: Atomic UPDATE ensures exactly one re-registration wins.
        """
        email = "expired_attack@example.com"

        # Setup: Create EXPIRED registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code, state)
                   VALUES (%s, NULL, '0000', 'EXPIRED')""",
                (email,),
            )
            conn.commit()

        results: list[bool] = []
        results_lock = threading.Lock()
        num_attackers = 5

        def attack_reregister(attacker_id: int) -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.claim_email(email, f"$2b$10$attacker{attacker_id}hash", "9999")
            with results_lock:
                results.append(result)

        # Launch concurrent re-registration attack
        with ThreadPoolExecutor(max_workers=num_attackers) as executor:
            futures = [
                executor.submit(attack_reregister, i) for i in range(num_attackers)
            ]
            for f in futures:
                f.result()

        # Defense verification: exactly one should succeed
        # First UPDATE changes state to CLAIMED, others see CLAIMED and fail
        assert results.count(True) == 1, (
            f"Re-registration race condition: {results.count(True)} succeeded "
            f"(expected exactly 1)"
        )

        # Verify database consistency
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "CLAIMED", "State should be CLAIMED after successful re-registration"
        assert row[1] == 0, "Attempt count should reset to 0"

    def test_concurrent_activation_no_double_activation(
        self, pool: ConnectionPool
    ) -> None:
        """
        Simulate attack attempting to activate same account concurrently.

        Attack scenario: Attacker intercepts valid credentials and attempts
        multiple concurrent activations hoping to cause inconsistent state.

        Expected defense: SELECT FOR UPDATE locks row, ensuring atomic state
        transition - only first activation succeeds.
        """
        email = "doubleactivate@example.com"
        password = "password123"
        code = "1234"
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()

        # Setup: Create CLAIMED registration
        with pool.connection() as conn:
            conn.execute(
                """INSERT INTO registrations (email, password_hash, verification_code)
                   VALUES (%s, %s, %s)""",
                (email, password_hash, code),
            )
            conn.commit()

        results: list[VerifyResult] = []
        results_lock = threading.Lock()
        num_attackers = 5

        def attack_activate() -> None:
            repo = PostgresRegistrationRepository(pool)
            result = repo.verify_and_activate(email, code, password)
            with results_lock:
                results.append(result)

        # Launch concurrent activation attack
        with ThreadPoolExecutor(max_workers=num_attackers) as executor:
            futures = [executor.submit(attack_activate) for _ in range(num_attackers)]
            for f in futures:
                f.result()

        # Defense verification: exactly one SUCCESS, others NOT_FOUND
        # (NOT_FOUND because account is now ACTIVE, not CLAIMED)
        success_count = results.count(VerifyResult.SUCCESS)
        not_found_count = results.count(VerifyResult.NOT_FOUND)

        assert success_count == 1, (
            f"Double activation vulnerability: {success_count} activations succeeded "
            f"(expected exactly 1)"
        )
        assert not_found_count == num_attackers - 1, (
            f"Subsequent activations should return NOT_FOUND (got {not_found_count})"
        )

        # Verify database shows exactly one ACTIVE state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, activated_at FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row[0] == "ACTIVE", "Final state should be ACTIVE"
        assert row[1] is not None, "activated_at should be set"


class TestDataIntegrityUnderConcurrency:
    """
    Verify data integrity is maintained under adversarial concurrent access.

    These tests verify that no data corruption occurs even when
    attackers attempt to exploit race conditions.
    """

    def test_no_data_corruption_under_concurrent_claims(
        self, pool: ConnectionPool
    ) -> None:
        """
        Verify registration data remains consistent under concurrent attack.

        After concurrent registration attempts, the winning registration
        should have complete, uncorrupted data.
        """
        email = "integrity@example.com"
        expected_hash = "$2b$10$winnerhash"
        expected_code = "5555"

        results: list[tuple[bool, str, str]] = []
        results_lock = threading.Lock()

        def attack_register(attacker_id: int) -> None:
            repo = PostgresRegistrationRepository(pool)
            hash_val = expected_hash if attacker_id == 0 else f"$2b$10$loser{attacker_id}"
            code_val = expected_code if attacker_id == 0 else f"{attacker_id:04d}"
            result = repo.claim_email(email, hash_val, code_val)
            with results_lock:
                results.append((result, hash_val, code_val))

        # Launch concurrent attack with different credentials
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(attack_register, i) for i in range(5)]
            for f in futures:
                f.result()

        # Find winning registration's expected values
        winner = next((r for r in results if r[0] is True), None)
        assert winner is not None, "At least one registration should succeed"

        # Verify database has consistent data (from winner only)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash, verification_code, state, attempt_count "
                "FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None, "Registration should exist"
        assert row[0] == winner[1], "Password hash should match winner's value"
        assert row[1] == winner[2], "Verification code should match winner's value"
        assert row[2] == "CLAIMED", "State should be CLAIMED"
        assert row[3] == 0, "Attempt count should be 0"

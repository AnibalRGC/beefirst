"""
Integration tests for registration flow.

Tests the full registration flow through the API with real database.
Requires PostgreSQL to be running (via docker-compose).
"""

import logging
import re
from base64 import b64encode

import pytest
from fastapi.testclient import TestClient
from psycopg_pool import ConnectionPool

from src.api.main import app
from src.config.settings import get_settings


@pytest.fixture(scope="module")
def pool() -> ConnectionPool:
    """Create connection pool for integration tests."""
    settings = get_settings()
    pool = ConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        open=True,
    )
    yield pool
    pool.close()


@pytest.fixture(autouse=True)
def clean_database(pool: ConnectionPool) -> None:
    """Clean registrations table before each test."""
    with pool.connection() as conn:
        conn.execute("DELETE FROM registrations")
        conn.commit()
    yield


@pytest.fixture
def client(pool: ConnectionPool) -> TestClient:
    """Create test client with real database connection."""
    # Override the app's pool with our test pool
    app.state.pool = pool
    return TestClient(app)


def basic_auth_header(email: str, password: str) -> dict:
    """Create HTTP BASIC AUTH header for testing."""
    credentials = f"{email}:{password}"
    encoded = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


class TestRegisterFlow:
    """Integration tests for POST /v1/register."""

    def test_full_registration_flow(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """End-to-end registration with verification code in logs."""
        with caplog.at_level(logging.INFO):
            response = client.post(
                "/v1/register",
                json={"email": "integration@example.com", "password": "secure123"},
            )

        assert response.status_code == 201
        assert response.json() == {
            "message": "Verification code sent",
            "email": "integration@example.com",
            "expires_in_seconds": 60,
        }
        # Verify code appears in logs
        assert "[VERIFICATION]" in caplog.text
        assert "integration@example.com" in caplog.text

    def test_email_normalization_through_stack(
        self, client: TestClient, pool: ConnectionPool
    ) -> None:
        """Email is normalized through the full stack."""
        response = client.post(
            "/v1/register",
            json={"email": "  USER@Example.COM  ", "password": "secure123"},
        )

        assert response.status_code == 201

        # Verify email was normalized in database
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT email FROM registrations")
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "user@example.com"

    def test_duplicate_registration_returns_409(self, client: TestClient) -> None:
        """Duplicate registration attempt returns 409 with generic message."""
        # First registration succeeds
        response1 = client.post(
            "/v1/register",
            json={"email": "duplicate@example.com", "password": "secure123"},
        )
        assert response1.status_code == 201

        # Second registration fails
        response2 = client.post(
            "/v1/register",
            json={"email": "duplicate@example.com", "password": "different456"},
        )
        assert response2.status_code == 409
        assert response2.json() == {"detail": "Registration failed"}

    def test_registration_creates_claimed_record(
        self, client: TestClient, pool: ConnectionPool
    ) -> None:
        """Registration creates record with CLAIMED state."""
        response = client.post(
            "/v1/register",
            json={"email": "state@example.com", "password": "secure123"},
        )
        assert response.status_code == 201

        # Verify record state in database
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                ("state@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "CLAIMED"
        assert row[1] == 0

    def test_registration_stores_hashed_password(
        self, client: TestClient, pool: ConnectionPool
    ) -> None:
        """Registration stores bcrypt-hashed password."""
        response = client.post(
            "/v1/register",
            json={"email": "hashed@example.com", "password": "secure123"},
        )
        assert response.status_code == 201

        # Verify password is hashed (bcrypt format)
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT password_hash FROM registrations WHERE email = %s",
                ("hashed@example.com",),
            )
            row = cursor.fetchone()

        assert row is not None
        password_hash = row[0]
        # bcrypt hashes start with $2b$
        assert password_hash.startswith("$2b$")

    def test_verification_code_in_log_format(
        self, client: TestClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Verification code is logged in correct format."""
        with caplog.at_level(logging.INFO):
            client.post(
                "/v1/register",
                json={"email": "logformat@example.com", "password": "secure123"},
            )

        # Check log format: [VERIFICATION] Email: ... Code: ...
        assert "Email: logformat@example.com" in caplog.text
        assert "Code:" in caplog.text

    def test_different_emails_can_register(self, client: TestClient) -> None:
        """Multiple different emails can register successfully."""
        emails = ["user1@example.com", "user2@example.com", "user3@example.com"]

        for email in emails:
            response = client.post(
                "/v1/register",
                json={"email": email, "password": "secure123"},
            )
            assert response.status_code == 201


class TestActivationFlow:
    """Integration tests for the complete Trust Loop: register → activate."""

    def test_full_registration_and_activation_flow(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """
        End-to-end: register → extract code → activate → verify ACTIVE.

        This test verifies the complete Trust Loop:
        1. User registers with email and password
        2. System generates and logs verification code
        3. User activates account with code via BASIC AUTH
        4. System transitions state from CLAIMED to ACTIVE
        """
        email = "e2e@example.com"
        password = "secure123"

        # Step 1: Register user
        with caplog.at_level(logging.INFO):
            register_response = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )

        assert register_response.status_code == 201
        assert register_response.json()["email"] == email

        # Step 2: Extract verification code from logs
        # Log format: [VERIFICATION] Email: e2e@example.com Code: 1234
        log_text = caplog.text
        match = re.search(r"Code: (\d{4})", log_text)
        assert match is not None, "Verification code not found in logs"
        verification_code = match.group(1)

        # Verify state is CLAIMED before activation
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, activated_at FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row is not None
        assert row[0] == "CLAIMED"
        assert row[1] is None  # activated_at not set yet

        # Step 3: Activate account with BASIC AUTH
        activate_response = client.post(
            "/v1/activate",
            json={"code": verification_code},
            headers=basic_auth_header(email, password),
        )

        assert activate_response.status_code == 200
        assert activate_response.json() == {
            "message": "Account activated",
            "email": email,
        }

        # Step 4: Verify state is ACTIVE and activated_at is set
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, activated_at FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE"
        assert row[1] is not None  # activated_at should now be set

    def test_activation_with_wrong_code_fails(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Activation with wrong verification code returns 401."""
        email = "wrongcode@example.com"
        password = "secure123"

        # Register user
        with caplog.at_level(logging.INFO):
            client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )

        # Try to activate with wrong code
        activate_response = client.post(
            "/v1/activate",
            json={"code": "9999"},  # Wrong code
            headers=basic_auth_header(email, password),
        )

        assert activate_response.status_code == 401
        assert activate_response.json() == {"detail": "Invalid credentials or code"}

    def test_activation_with_wrong_password_fails(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Activation with wrong password returns 401."""
        email = "wrongpwd@example.com"
        password = "secure123"

        # Register user and extract code
        with caplog.at_level(logging.INFO):
            client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )

        log_text = caplog.text
        match = re.search(r"Code: (\d{4})", log_text)
        assert match is not None
        verification_code = match.group(1)

        # Try to activate with wrong password
        activate_response = client.post(
            "/v1/activate",
            json={"code": verification_code},
            headers=basic_auth_header(email, "wrongpassword"),
        )

        assert activate_response.status_code == 401
        assert activate_response.json() == {"detail": "Invalid credentials or code"}

    def test_activation_with_normalized_email(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Activation works with denormalized email (case-insensitive)."""
        email = "normalize@example.com"
        password = "secure123"

        # Register with normalized email
        with caplog.at_level(logging.INFO):
            client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )

        log_text = caplog.text
        match = re.search(r"Code: (\d{4})", log_text)
        assert match is not None
        verification_code = match.group(1)

        # Activate with denormalized email (uppercase, spaces)
        activate_response = client.post(
            "/v1/activate",
            json={"code": verification_code},
            headers=basic_auth_header("  NORMALIZE@EXAMPLE.COM  ", password),
        )

        assert activate_response.status_code == 200

        # Verify state is ACTIVE
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE"

    def test_activation_without_registration_fails(self, client: TestClient) -> None:
        """Activation without prior registration returns 401."""
        activate_response = client.post(
            "/v1/activate",
            json={"code": "1234"},
            headers=basic_auth_header("nonexistent@example.com", "password"),
        )

        assert activate_response.status_code == 401
        assert activate_response.json() == {"detail": "Invalid credentials or code"}

    def test_activation_after_3_failed_attempts_locks_account(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Account locks after 3 failed activation attempts."""
        email = "lockout@example.com"
        password = "secure123"

        # Register user and extract code
        with caplog.at_level(logging.INFO):
            client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )

        log_text = caplog.text
        match = re.search(r"Code: (\d{4})", log_text)
        assert match is not None
        correct_code = match.group(1)

        # Make 3 failed attempts
        for _ in range(3):
            response = client.post(
                "/v1/activate",
                json={"code": "0000"},  # Wrong code
                headers=basic_auth_header(email, password),
            )
            assert response.status_code == 401

        # Verify account is LOCKED
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state, attempt_count FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "LOCKED"
        assert row[1] == 3

        # Even correct code should now fail
        response = client.post(
            "/v1/activate",
            json={"code": correct_code},
            headers=basic_auth_header(email, password),
        )
        assert response.status_code == 401


class TestRegisterValidation:
    """Integration tests for request validation."""

    def test_invalid_email_returns_422(self, client: TestClient) -> None:
        """Invalid email format returns 422."""
        response = client.post(
            "/v1/register",
            json={"email": "not-an-email", "password": "secure123"},
        )
        assert response.status_code == 422

    def test_short_password_returns_422(self, client: TestClient) -> None:
        """Password shorter than 8 characters returns 422."""
        response = client.post(
            "/v1/register",
            json={"email": "valid@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_missing_email_returns_422(self, client: TestClient) -> None:
        """Missing email field returns 422."""
        response = client.post(
            "/v1/register",
            json={"password": "secure123"},
        )
        assert response.status_code == 422

    def test_missing_password_returns_422(self, client: TestClient) -> None:
        """Missing password field returns 422."""
        response = client.post(
            "/v1/register",
            json={"email": "valid@example.com"},
        )
        assert response.status_code == 422


class TestReRegistrationFlow:
    """E2E tests for email release and re-registration - FR17, FR26.

    These tests verify the full re-registration flow through the API:
    - EXPIRED emails can be re-registered
    - LOCKED emails can be re-registered
    - New verification codes work, old codes don't
    """

    def test_full_reregistration_flow_after_expiration(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Complete re-registration flow after expiration (AC6).

        1. Register with email and password
        2. Let registration expire (manipulate DB)
        3. Re-register with same email and new password
        4. Verify new code works and old code doesn't
        """
        email = "reregister@example.com"
        first_password = "firstpassword123"
        second_password = "secondpassword456"

        # Step 1: First registration
        with caplog.at_level(logging.INFO):
            response1 = client.post(
                "/v1/register",
                json={"email": email, "password": first_password},
            )
        assert response1.status_code == 201

        # Extract first verification code
        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None
        first_code = match.group(1)

        # Step 2: Expire the registration (simulate by setting state to EXPIRED)
        with pool.connection() as conn:
            conn.execute(
                "UPDATE registrations SET state = 'EXPIRED', password_hash = NULL WHERE email = %s",
                (email,),
            )
            conn.commit()

        # Step 3: Re-register with new password
        caplog.clear()
        with caplog.at_level(logging.INFO):
            response2 = client.post(
                "/v1/register",
                json={"email": email, "password": second_password},
            )
        assert response2.status_code == 201, "Re-registration should succeed for EXPIRED email"

        # Extract second verification code
        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None
        second_code = match.group(1)

        # AC7: Verify verification codes are different
        assert first_code != second_code, (
            f"Verification codes must change on re-registration (AC7). Got same code: {first_code}"
        )

        # Step 4: Verify OLD code fails (AC7)
        response_old = client.post(
            "/v1/activate",
            json={"code": first_code},
            headers=basic_auth_header(email, second_password),
        )
        assert response_old.status_code == 401, "Old code should fail after re-registration"

        # Step 5: Verify NEW code succeeds
        response_new = client.post(
            "/v1/activate",
            json={"code": second_code},
            headers=basic_auth_header(email, second_password),
        )
        assert response_new.status_code == 200, "New code should succeed"

        # Verify final state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE"

    def test_reregistration_after_lockout(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Re-registration succeeds after account lockout (FR17).

        1. Register with email
        2. Lock account via 3 failed attempts
        3. Re-register with same email
        4. Verify new registration works
        """
        email = "lockedreregister@example.com"
        password = "secure123"

        # Step 1: Register
        with caplog.at_level(logging.INFO):
            response1 = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )
        assert response1.status_code == 201

        # Step 2: Lock account via 3 failed attempts
        for _ in range(3):
            client.post(
                "/v1/activate",
                json={"code": "0000"},  # Wrong code
                headers=basic_auth_header(email, password),
            )

        # Verify account is LOCKED
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == "LOCKED"

        # Step 3: Re-register
        caplog.clear()
        with caplog.at_level(logging.INFO):
            response2 = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )
        assert response2.status_code == 201, "Re-registration should succeed for LOCKED email"

        # Extract new verification code
        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None
        new_code = match.group(1)

        # Step 4: Verify new registration can be activated
        response_activate = client.post(
            "/v1/activate",
            json={"code": new_code},
            headers=basic_auth_header(email, password),
        )
        assert response_activate.status_code == 200

        # Verify final state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "ACTIVE"

    def test_old_code_fails_after_reregistration(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Old verification code is rejected after re-registration (AC7).

        Explicitly tests that the OLD code from before expiration
        cannot be used after re-registration.
        """
        email = "oldcode@example.com"
        password = "secure123"

        # Step 1: First registration
        with caplog.at_level(logging.INFO):
            response1 = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )
        assert response1.status_code == 201

        # Extract first code
        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None
        first_code = match.group(1)

        # Step 2: Expire the registration
        with pool.connection() as conn:
            conn.execute(
                "UPDATE registrations SET state = 'EXPIRED', password_hash = NULL WHERE email = %s",
                (email,),
            )
            conn.commit()

        # Step 3: Re-register
        caplog.clear()
        with caplog.at_level(logging.INFO):
            response2 = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )
        assert response2.status_code == 201

        # Extract second code to verify it works later
        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None, "New verification code should be generated"
        second_code = match.group(1)

        # Step 4: Try OLD code - must fail (AC7)
        response_old = client.post(
            "/v1/activate",
            json={"code": first_code},
            headers=basic_auth_header(email, password),
        )
        assert response_old.status_code == 401, (
            "Old verification code must fail after re-registration (AC7)"
        )

        # Step 5: Verify NEW code succeeds (complete AC7)
        response_new = client.post(
            "/v1/activate",
            json={"code": second_code},
            headers=basic_auth_header(email, password),
        )
        assert response_new.status_code == 200, "New verification code should succeed"

    def test_reregistration_fails_for_active_account(
        self,
        client: TestClient,
        caplog: pytest.LogCaptureFixture,
        pool: ConnectionPool,
    ) -> None:
        """Re-registration fails for already ACTIVE accounts.

        Users cannot re-register with an email that has been successfully activated.
        """
        email = "activeaccount@example.com"
        password = "secure123"

        # Step 1: Register and activate
        with caplog.at_level(logging.INFO):
            response1 = client.post(
                "/v1/register",
                json={"email": email, "password": password},
            )
        assert response1.status_code == 201

        match = re.search(r"Code: (\d{4})", caplog.text)
        assert match is not None
        code = match.group(1)

        response_activate = client.post(
            "/v1/activate",
            json={"code": code},
            headers=basic_auth_header(email, password),
        )
        assert response_activate.status_code == 200

        # Verify ACTIVE state
        with pool.connection() as conn, conn.cursor() as cursor:
            cursor.execute(
                "SELECT state FROM registrations WHERE email = %s",
                (email,),
            )
            row = cursor.fetchone()
        assert row[0] == "ACTIVE"

        # Step 2: Attempt re-registration - should fail
        response2 = client.post(
            "/v1/register",
            json={"email": email, "password": "newpassword123"},
        )
        assert response2.status_code == 409, "Re-registration should fail for ACTIVE email"

    def test_reregistration_fails_for_inprogress_registration(
        self,
        client: TestClient,
    ) -> None:
        """Re-registration fails for in-progress (CLAIMED) registrations.

        If a registration is already in progress, the second attempt should fail.
        """
        email = "inprogress@example.com"

        # First registration
        response1 = client.post(
            "/v1/register",
            json={"email": email, "password": "firstpassword123"},
        )
        assert response1.status_code == 201

        # Second registration attempt while first is still in progress
        response2 = client.post(
            "/v1/register",
            json={"email": email, "password": "secondpassword123"},
        )
        assert response2.status_code == 409, (
            "Re-registration should fail for CLAIMED email (let it expire naturally)"
        )


class TestHealthCheck:
    """Integration tests for the health check endpoint."""

    def test_health_check_returns_healthy(self, client: TestClient) -> None:
        """Health check endpoint returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_health_check_validates_database(
        self, client: TestClient, pool: ConnectionPool
    ) -> None:
        """Health check validates database connectivity."""
        # First verify database is working
        with pool.connection() as conn:
            conn.execute("SELECT 1")

        # Health check should succeed
        response = client.get("/health")
        assert response.status_code == 200


class TestAlreadyLockedAccount:
    """Tests for edge case where account is already locked in database."""

    def test_already_locked_account_returns_locked(
        self,
        client: TestClient,
        pool: ConnectionPool,
    ) -> None:
        """Account that is already LOCKED (attempt_count >= 3) returns LOCKED.

        This tests the edge case where the account was locked by a previous
        request and the current request sees it as already locked.
        """
        email = "prelocked@example.com"
        password = "secure123"

        # Directly insert a LOCKED account with attempt_count = 3
        # This simulates the edge case where account is already locked
        import bcrypt

        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt(10)).decode()
        with pool.connection() as conn:
            # Insert with CLAIMED state but attempt_count = 3
            # This tests the "already locked" branch in verify_and_activate
            conn.execute(
                """INSERT INTO registrations
                   (email, password_hash, verification_code, state, attempt_count)
                   VALUES (%s, %s, %s, 'CLAIMED', 3)""",
                (email, password_hash, "1234"),
            )
            conn.commit()

        # Try to activate - should return LOCKED because attempt_count >= 3
        response = client.post(
            "/v1/activate",
            json={"code": "1234"},
            headers=basic_auth_header(email, password),
        )
        assert response.status_code == 401

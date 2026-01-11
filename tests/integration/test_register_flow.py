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

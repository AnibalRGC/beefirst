"""
Integration tests for registration flow.

Tests the full registration flow through the API with real database.
Requires PostgreSQL to be running (via docker-compose).
"""

import logging

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

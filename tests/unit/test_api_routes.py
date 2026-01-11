"""
Unit tests for API v1 routes.

Tests endpoint responses with mocked dependencies.
"""

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_registration_service
from src.api.v1.routes import router
from src.domain.exceptions import EmailAlreadyClaimed
from src.domain.registration import RegistrationService


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/v1")

    # Mock the app.state.pool for dependency injection
    test_app.state.pool = MagicMock()

    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client for the application."""
    return TestClient(app)


class TestRegisterEndpoint:
    """Tests for POST /v1/register endpoint."""

    def test_register_success_returns_201(self, app: FastAPI) -> None:
        """Successful registration returns 201 Created."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.register.return_value = "user@example.com"

        def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/register",
                json={"email": "user@example.com", "password": "secure123"},
            )

            assert response.status_code == 201
            assert response.json() == {
                "message": "Verification code sent",
                "email": "user@example.com",
                "expires_in_seconds": 60,
            }
            mock_service.register.assert_called_once_with("user@example.com", "secure123")
        finally:
            app.dependency_overrides.clear()

    def test_register_duplicate_returns_409(self, app: FastAPI) -> None:
        """Duplicate email returns 409 Conflict with generic message."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.register.side_effect = EmailAlreadyClaimed("user@example.com")

        def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/register",
                json={"email": "user@example.com", "password": "secure123"},
            )

            assert response.status_code == 409
            assert response.json() == {"detail": "Registration failed"}
        finally:
            app.dependency_overrides.clear()

    def test_register_validates_email(self, client: TestClient) -> None:
        """Register endpoint validates email format."""
        response = client.post(
            "/v1/register",
            json={"email": "invalid-email", "password": "secure123"},
        )
        assert response.status_code == 422

    def test_register_validates_password_length(self, client: TestClient) -> None:
        """Register endpoint validates password minimum length."""
        response = client.post(
            "/v1/register",
            json={"email": "user@example.com", "password": "short"},
        )
        assert response.status_code == 422

    def test_register_requires_email(self, client: TestClient) -> None:
        """Register endpoint requires email field."""
        response = client.post(
            "/v1/register",
            json={"password": "secure123"},
        )
        assert response.status_code == 422

    def test_register_requires_password(self, client: TestClient) -> None:
        """Register endpoint requires password field."""
        response = client.post(
            "/v1/register",
            json={"email": "user@example.com"},
        )
        assert response.status_code == 422

    def test_register_error_message_is_generic(self, app: FastAPI) -> None:
        """Error message is generic to prevent email enumeration."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.register.side_effect = EmailAlreadyClaimed("user@example.com")

        def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/register",
                json={"email": "user@example.com", "password": "secure123"},
            )

            # Error message should NOT contain the email
            response_text = response.text
            assert "user@example.com" not in response_text
            assert response.json()["detail"] == "Registration failed"
        finally:
            app.dependency_overrides.clear()


class TestActivateEndpoint:
    """Tests for POST /v1/activate endpoint."""

    def test_activate_returns_501_stub(self, client: TestClient) -> None:
        """Activate endpoint returns 501 Not Implemented (stub)."""
        response = client.post(
            "/v1/activate",
            json={"code": "1234"},
        )
        assert response.status_code == 501
        assert response.json() == {"detail": "Activation not yet implemented"}

    def test_activate_validates_code_length_short(self, client: TestClient) -> None:
        """Activate endpoint validates code minimum length."""
        response = client.post(
            "/v1/activate",
            json={"code": "123"},
        )
        assert response.status_code == 422

    def test_activate_validates_code_length_long(self, client: TestClient) -> None:
        """Activate endpoint validates code maximum length."""
        response = client.post(
            "/v1/activate",
            json={"code": "12345"},
        )
        assert response.status_code == 422

    def test_activate_validates_code_numeric(self, client: TestClient) -> None:
        """Activate endpoint validates code is numeric."""
        response = client.post(
            "/v1/activate",
            json={"code": "abcd"},
        )
        assert response.status_code == 422

    def test_activate_requires_code(self, client: TestClient) -> None:
        """Activate endpoint requires code field."""
        response = client.post(
            "/v1/activate",
            json={},
        )
        assert response.status_code == 422

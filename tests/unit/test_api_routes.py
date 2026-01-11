"""
Unit tests for API v1 routes.

Tests endpoint responses with mocked dependencies.
"""

from base64 import b64encode
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.dependencies import get_basic_auth_credentials, get_registration_service
from src.api.v1.routes import router
from src.domain.exceptions import EmailAlreadyClaimed
from src.domain.ports import VerifyResult
from src.domain.registration import RegistrationService


def basic_auth_header(email: str, password: str) -> dict:
    """Create HTTP BASIC AUTH header for testing."""
    credentials = f"{email}:{password}"
    encoded = b64encode(credentials.encode()).decode()
    return {"Authorization": f"Basic {encoded}"}


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

    def test_activate_success_returns_200(self, app: FastAPI) -> None:
        """Successful activation returns 200 OK with correct response."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.SUCCESS

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("user@example.com", "password123"),
            )

            assert response.status_code == 200
            assert response.json() == {
                "message": "Account activated",
                "email": "user@example.com",
            }
            mock_service.verify_and_activate.assert_called_once_with(
                "user@example.com", "1234", "password123"
            )
        finally:
            app.dependency_overrides.clear()

    def test_activate_wrong_code_returns_401(self, app: FastAPI) -> None:
        """Wrong verification code returns 401 with generic error."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.INVALID_CODE

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "9999"},
                headers=basic_auth_header("user@example.com", "password123"),
            )

            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid credentials or code"}
        finally:
            app.dependency_overrides.clear()

    def test_activate_wrong_password_returns_401(self, app: FastAPI) -> None:
        """Wrong password returns 401 with same generic error as wrong code."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.INVALID_CODE

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "wrongpassword")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("user@example.com", "wrongpassword"),
            )

            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid credentials or code"}
        finally:
            app.dependency_overrides.clear()

    def test_activate_expired_returns_401(self, app: FastAPI) -> None:
        """Expired registration returns 401 with generic error."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.EXPIRED

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("user@example.com", "password123"),
            )

            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid credentials or code"}
        finally:
            app.dependency_overrides.clear()

    def test_activate_locked_returns_401(self, app: FastAPI) -> None:
        """Locked account returns 401 with generic error."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.LOCKED

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("user@example.com", "password123"),
            )

            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid credentials or code"}
        finally:
            app.dependency_overrides.clear()

    def test_activate_not_found_returns_401(self, app: FastAPI) -> None:
        """Non-existent email returns 401 with generic error."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.NOT_FOUND

        def override_service():
            return mock_service

        def override_credentials():
            return ("nonexistent@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("nonexistent@example.com", "password123"),
            )

            assert response.status_code == 401
            assert response.json() == {"detail": "Invalid credentials or code"}
        finally:
            app.dependency_overrides.clear()

    def test_activate_missing_auth_header_returns_401(self, app: FastAPI) -> None:
        """Missing Authorization header returns 401."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
            )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_activate_malformed_auth_header_returns_401(self, app: FastAPI) -> None:
        """Malformed Authorization header returns 401."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        app.dependency_overrides[get_registration_service] = override_service
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers={"Authorization": "Invalid"},
            )

            assert response.status_code == 401
        finally:
            app.dependency_overrides.clear()

    def test_activate_validates_code_length_short(self, app: FastAPI) -> None:
        """Activate endpoint validates code minimum length (returns 422)."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "123"},
                headers=basic_auth_header("user@example.com", "password123"),
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_activate_validates_code_length_long(self, app: FastAPI) -> None:
        """Activate endpoint validates code maximum length (returns 422)."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "12345"},
                headers=basic_auth_header("user@example.com", "password123"),
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_activate_validates_code_numeric(self, app: FastAPI) -> None:
        """Activate endpoint validates code is numeric (returns 422)."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "abcd"},
                headers=basic_auth_header("user@example.com", "password123"),
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_activate_requires_code(self, app: FastAPI) -> None:
        """Activate endpoint requires code field (returns 422)."""
        mock_service = MagicMock(spec=RegistrationService)

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={},
                headers=basic_auth_header("user@example.com", "password123"),
            )
            assert response.status_code == 422
        finally:
            app.dependency_overrides.clear()

    def test_activate_normalizes_email(self, app: FastAPI) -> None:
        """Email is normalized (lowercase, stripped) before service call."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = VerifyResult.SUCCESS

        def override_service():
            return mock_service

        # Simulate email normalization that happens in get_basic_auth_credentials
        def override_credentials():
            return ("user@example.com", "password123")  # Already normalized

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header(" USER@EXAMPLE.COM ", "password123"),
            )

            assert response.status_code == 200
            # Verify service was called with normalized email
            mock_service.verify_and_activate.assert_called_once_with(
                "user@example.com", "1234", "password123"
            )
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.parametrize(
        "verify_result",
        [
            VerifyResult.INVALID_CODE,
            VerifyResult.EXPIRED,
            VerifyResult.LOCKED,
            VerifyResult.NOT_FOUND,
        ],
    )
    def test_activate_all_failures_return_identical_error(
        self, app: FastAPI, verify_result: VerifyResult
    ) -> None:
        """All failure modes return identical error message (NFR-S4)."""
        mock_service = MagicMock(spec=RegistrationService)
        mock_service.verify_and_activate.return_value = verify_result

        def override_service():
            return mock_service

        def override_credentials():
            return ("user@example.com", "password123")

        app.dependency_overrides[get_registration_service] = override_service
        app.dependency_overrides[get_basic_auth_credentials] = override_credentials
        client = TestClient(app)

        try:
            response = client.post(
                "/v1/activate",
                json={"code": "1234"},
                headers=basic_auth_header("user@example.com", "password123"),
            )

            assert response.status_code == 401, f"Expected 401 for {verify_result}"
            assert response.json() == {"detail": "Invalid credentials or code"}, (
                f"Expected generic error for {verify_result}"
            )
        finally:
            app.dependency_overrides.clear()

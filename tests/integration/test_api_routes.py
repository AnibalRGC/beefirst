"""
Integration tests for API v1 routes.

Tests endpoint responses without requiring database connection.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.api.v1.routes import router


@pytest.fixture
def app() -> FastAPI:
    """Create test FastAPI application with v1 router."""
    test_app = FastAPI()
    test_app.include_router(router, prefix="/v1")
    return test_app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    """Create test client for the application."""
    return TestClient(app)


class TestRegisterEndpoint:
    """Tests for POST /v1/register endpoint."""

    def test_register_returns_501_stub(self, client: TestClient) -> None:
        """Register endpoint returns 501 Not Implemented (stub)."""
        response = client.post(
            "/v1/register",
            json={"email": "user@example.com", "password": "secure123"},
        )
        assert response.status_code == 501
        assert response.json() == {"detail": "Registration not yet implemented"}

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

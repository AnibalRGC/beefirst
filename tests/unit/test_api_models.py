"""
Unit tests for API request/response models.

Tests Pydantic model validation for registration and activation endpoints.
"""

import pytest
from pydantic import ValidationError

from src.api.models import (
    ActivateRequest,
    ActivateResponse,
    ErrorResponse,
    RegisterRequest,
    RegisterResponse,
)


class TestRegisterRequest:
    """Tests for RegisterRequest model."""

    def test_valid_register_request(self) -> None:
        """Valid email and password are accepted."""
        request = RegisterRequest(email="user@example.com", password="secure123")
        assert request.email == "user@example.com"
        assert request.password == "secure123"

    def test_email_domain_normalized(self) -> None:
        """EmailStr normalizes domain to lowercase."""
        request = RegisterRequest(email="USER@EXAMPLE.COM", password="secure123")
        # Pydantic EmailStr normalizes domain to lowercase
        assert request.email == "USER@example.com"

    def test_invalid_email_rejected(self) -> None:
        """Invalid email format raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="not-an-email", password="secure123")
        assert "email" in str(exc_info.value)

    def test_password_minimum_length(self) -> None:
        """Password shorter than 8 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(email="user@example.com", password="short")
        assert "password" in str(exc_info.value)

    def test_password_exactly_8_chars(self) -> None:
        """Password with exactly 8 characters is accepted."""
        request = RegisterRequest(email="user@example.com", password="exactly8")
        assert request.password == "exactly8"

    def test_missing_email_rejected(self) -> None:
        """Missing email raises ValidationError."""
        with pytest.raises(ValidationError):
            RegisterRequest(password="secure123")  # type: ignore[call-arg]

    def test_missing_password_rejected(self) -> None:
        """Missing password raises ValidationError."""
        with pytest.raises(ValidationError):
            RegisterRequest(email="user@example.com")  # type: ignore[call-arg]


class TestRegisterResponse:
    """Tests for RegisterResponse model."""

    def test_valid_register_response(self) -> None:
        """Valid response fields are accepted."""
        response = RegisterResponse(message="Verification code sent", expires_in_seconds=60)
        assert response.message == "Verification code sent"
        assert response.expires_in_seconds == 60


class TestActivateRequest:
    """Tests for ActivateRequest model."""

    def test_valid_4_digit_code(self) -> None:
        """4-digit numeric code is accepted."""
        request = ActivateRequest(code="1234")
        assert request.code == "1234"

    def test_code_too_short_rejected(self) -> None:
        """Code shorter than 4 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivateRequest(code="123")
        assert "code" in str(exc_info.value)

    def test_code_too_long_rejected(self) -> None:
        """Code longer than 4 characters raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivateRequest(code="12345")
        assert "code" in str(exc_info.value)

    def test_non_numeric_code_rejected(self) -> None:
        """Non-numeric code raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            ActivateRequest(code="abcd")
        assert "code" in str(exc_info.value)

    def test_missing_code_rejected(self) -> None:
        """Missing code raises ValidationError."""
        with pytest.raises(ValidationError):
            ActivateRequest()  # type: ignore[call-arg]


class TestActivateResponse:
    """Tests for ActivateResponse model."""

    def test_valid_activate_response(self) -> None:
        """Valid response fields are accepted."""
        response = ActivateResponse(message="Account activated", email="user@example.com")
        assert response.message == "Account activated"
        assert response.email == "user@example.com"


class TestErrorResponse:
    """Tests for ErrorResponse model."""

    def test_valid_error_response(self) -> None:
        """Valid error response is accepted."""
        response = ErrorResponse(detail="Registration failed")
        assert response.detail == "Registration failed"

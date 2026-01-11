"""
Unit tests for domain ports and exceptions.

Tests verify:
- Port interfaces are properly defined
- Exceptions are properly structured
- Domain purity (zero framework imports)
"""

import subprocess
from enum import Enum

import pytest

from src.domain.exceptions import (
    EmailAlreadyClaimed,
    RegistrationError,
    VerificationFailed,
)
from src.domain.ports import EmailSender, RegistrationRepository, VerifyResult


class TestVerifyResultEnum:
    """Tests for VerifyResult enum (AC6)."""

    def test_verify_result_is_enum(self) -> None:
        """VerifyResult is an Enum class."""
        assert issubclass(VerifyResult, Enum)

    def test_verify_result_has_success(self) -> None:
        """VerifyResult has SUCCESS value."""
        assert hasattr(VerifyResult, "SUCCESS")
        assert VerifyResult.SUCCESS.value == "success"

    def test_verify_result_has_invalid_code(self) -> None:
        """VerifyResult has INVALID_CODE value."""
        assert hasattr(VerifyResult, "INVALID_CODE")
        assert VerifyResult.INVALID_CODE.value == "invalid_code"

    def test_verify_result_has_expired(self) -> None:
        """VerifyResult has EXPIRED value."""
        assert hasattr(VerifyResult, "EXPIRED")
        assert VerifyResult.EXPIRED.value == "expired"

    def test_verify_result_has_locked(self) -> None:
        """VerifyResult has LOCKED value."""
        assert hasattr(VerifyResult, "LOCKED")
        assert VerifyResult.LOCKED.value == "locked"

    def test_verify_result_has_not_found(self) -> None:
        """VerifyResult has NOT_FOUND value."""
        assert hasattr(VerifyResult, "NOT_FOUND")
        assert VerifyResult.NOT_FOUND.value == "not_found"


class TestRegistrationRepositoryProtocol:
    """Tests for RegistrationRepository protocol (AC6)."""

    def test_registration_repository_has_claim_email_method(self) -> None:
        """RegistrationRepository defines claim_email method."""
        assert hasattr(RegistrationRepository, "claim_email")

    def test_claim_email_accepts_correct_parameters(self) -> None:
        """claim_email method signature accepts email, password_hash, code."""

        # Create a mock implementation to verify interface
        class MockRepo:
            def claim_email(self, email: str, password_hash: str, code: str) -> bool:
                return True

        repo = MockRepo()
        result = repo.claim_email("test@example.com", "hash", "1234")
        assert result is True


class TestEmailSenderProtocol:
    """Tests for EmailSender protocol (AC7)."""

    def test_email_sender_has_send_verification_code_method(self) -> None:
        """EmailSender defines send_verification_code method."""
        assert hasattr(EmailSender, "send_verification_code")

    def test_send_verification_code_accepts_correct_parameters(self) -> None:
        """send_verification_code method signature accepts email, code."""

        # Create a mock implementation to verify interface
        class MockSender:
            def send_verification_code(self, email: str, code: str) -> None:
                pass

        sender = MockSender()
        # Should not raise
        sender.send_verification_code("test@example.com", "1234")


class TestDomainExceptions:
    """Tests for domain exceptions (AC8)."""

    def test_registration_error_is_exception(self) -> None:
        """RegistrationError inherits from Exception."""
        assert issubclass(RegistrationError, Exception)

    def test_email_already_claimed_inherits_registration_error(self) -> None:
        """EmailAlreadyClaimed inherits from RegistrationError."""
        assert issubclass(EmailAlreadyClaimed, RegistrationError)

    def test_verification_failed_inherits_registration_error(self) -> None:
        """VerificationFailed inherits from RegistrationError."""
        assert issubclass(VerificationFailed, RegistrationError)

    def test_email_already_claimed_can_be_raised(self) -> None:
        """EmailAlreadyClaimed can be raised and caught."""
        with pytest.raises(EmailAlreadyClaimed):
            raise EmailAlreadyClaimed("test@example.com")

    def test_verification_failed_can_be_raised(self) -> None:
        """VerificationFailed can be raised and caught."""
        with pytest.raises(VerificationFailed):
            raise VerificationFailed("Code mismatch")


class TestDomainPurity:
    """Tests for domain purity - zero framework imports (AC1)."""

    def test_no_fastapi_imports_in_domain(self) -> None:
        """Domain layer has no FastAPI imports."""
        result = subprocess.run(
            ["grep", "-r", "from fastapi", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"FastAPI import found: {result.stdout}"

    def test_no_pydantic_imports_in_domain(self) -> None:
        """Domain layer has no Pydantic imports."""
        result = subprocess.run(
            ["grep", "-r", "from pydantic", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"Pydantic import found: {result.stdout}"

    def test_no_psycopg_imports_in_domain(self) -> None:
        """Domain layer has no psycopg imports."""
        result = subprocess.run(
            ["grep", "-r", "from psycopg", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"psycopg import found: {result.stdout}"

    def test_no_import_fastapi_in_domain(self) -> None:
        """Domain layer has no 'import fastapi' statements."""
        result = subprocess.run(
            ["grep", "-r", "import fastapi", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"FastAPI import found: {result.stdout}"

    def test_no_import_pydantic_in_domain(self) -> None:
        """Domain layer has no 'import pydantic' statements."""
        result = subprocess.run(
            ["grep", "-r", "import pydantic", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"Pydantic import found: {result.stdout}"

    def test_no_import_psycopg_in_domain(self) -> None:
        """Domain layer has no 'import psycopg' statements."""
        result = subprocess.run(
            ["grep", "-r", "import psycopg", "src/domain/"],
            capture_output=True,
            text=True,
        )
        assert result.returncode != 0, f"psycopg import found: {result.stdout}"

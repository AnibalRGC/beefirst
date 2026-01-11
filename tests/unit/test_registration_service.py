"""
Unit tests for RegistrationService domain logic.

Tests domain logic with mocked ports to verify:
- Email normalization
- Verification code generation
- Password hashing
- Registration flow orchestration
- Exception handling
"""

import re
from unittest.mock import Mock

import bcrypt
import pytest

from src.domain.exceptions import EmailAlreadyClaimed
from src.domain.registration import RegistrationService


class TestEmailNormalization:
    """Tests for email normalization (AC3)."""

    def test_normalize_email_strips_whitespace(self) -> None:
        """Email normalization removes leading/trailing whitespace."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("  user@example.com  ", "password123")

        call_args = repo.claim_email.call_args[0]
        assert call_args[0] == "user@example.com"

    def test_normalize_email_lowercases(self) -> None:
        """Email normalization converts to lowercase."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("USER@EXAMPLE.COM", "password123")

        call_args = repo.claim_email.call_args[0]
        assert call_args[0] == "user@example.com"

    def test_normalize_email_combined(self) -> None:
        """Email normalization applies strip + lowercase together."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("  User@Example.COM  ", "password123")

        call_args = repo.claim_email.call_args[0]
        assert call_args[0] == "user@example.com"


class TestVerificationCodeGeneration:
    """Tests for verification code generation (AC4)."""

    def test_verification_code_is_4_digits(self) -> None:
        """Verification code is exactly 4 digits."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = sender.send_verification_code.call_args[0]
        code = call_args[1]

        assert len(code) == 4
        assert code.isdigit()

    def test_verification_code_is_string(self) -> None:
        """Verification code is a string (preserves leading zeros)."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = sender.send_verification_code.call_args[0]
        code = call_args[1]

        assert isinstance(code, str)

    def test_verification_code_pattern_valid(self) -> None:
        """Verification code matches 4-digit pattern (0000-9999)."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = sender.send_verification_code.call_args[0]
        code = call_args[1]

        assert re.match(r"^\d{4}$", code)

    def test_verification_codes_vary(self) -> None:
        """Verification codes are not always the same (randomness check)."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)

        codes = set()
        for _ in range(10):
            service.register("user@example.com", "password123")
            call_args = sender.send_verification_code.call_args[0]
            codes.add(call_args[1])

        # With 10 attempts, should get at least 2 different codes
        # (probability of all same is 1/10^12)
        assert len(codes) >= 2


class TestPasswordHashing:
    """Tests for password hashing (AC5)."""

    def test_password_is_hashed(self) -> None:
        """Password is hashed before storage (not plaintext)."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = repo.claim_email.call_args[0]
        password_hash = call_args[1]

        assert password_hash != "password123"
        assert password_hash.startswith("$2")  # bcrypt prefix

    def test_password_hash_is_bcrypt(self) -> None:
        """Password hash uses bcrypt algorithm."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = repo.claim_email.call_args[0]
        password_hash = call_args[1]

        # bcrypt hashes start with $2a$, $2b$, or $2y$
        assert re.match(r"^\$2[aby]\$", password_hash)

    def test_password_hash_cost_factor_at_least_10(self) -> None:
        """Password hash uses cost factor >= 10 (NFR-S1)."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = repo.claim_email.call_args[0]
        password_hash = call_args[1]

        # bcrypt format: $2b$XX$... where XX is cost factor
        cost_str = password_hash.split("$")[2]
        cost = int(cost_str)
        assert cost >= 10

    def test_password_hash_verifiable(self) -> None:
        """Password hash can be verified with bcrypt."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        call_args = repo.claim_email.call_args[0]
        password_hash = call_args[1]

        # Verify the hash matches the original password
        assert bcrypt.checkpw(b"password123", password_hash.encode())


class TestRegistrationFlow:
    """Tests for registration flow orchestration (AC2)."""

    def test_register_calls_repository_claim_email(self) -> None:
        """Register method calls repository.claim_email."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        repo.claim_email.assert_called_once()

    def test_register_calls_email_sender_on_success(self) -> None:
        """Register method sends verification code on successful claim."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("user@example.com", "password123")

        sender.send_verification_code.assert_called_once()

    def test_register_sends_to_normalized_email(self) -> None:
        """Verification code is sent to normalized email."""
        repo = Mock()
        repo.claim_email.return_value = True
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)
        service.register("  USER@EXAMPLE.COM  ", "password123")

        call_args = sender.send_verification_code.call_args[0]
        assert call_args[0] == "user@example.com"

    def test_register_does_not_send_email_on_claim_failure(self) -> None:
        """Email is not sent when claim fails."""
        repo = Mock()
        repo.claim_email.return_value = False
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)

        with pytest.raises(EmailAlreadyClaimed):
            service.register("user@example.com", "password123")

        sender.send_verification_code.assert_not_called()


class TestEmailAlreadyClaimedException:
    """Tests for EmailAlreadyClaimed exception handling."""

    def test_raises_email_already_claimed_when_claim_fails(self) -> None:
        """Raises EmailAlreadyClaimed when repository returns False."""
        repo = Mock()
        repo.claim_email.return_value = False
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)

        with pytest.raises(EmailAlreadyClaimed):
            service.register("user@example.com", "password123")

    def test_exception_contains_normalized_email(self) -> None:
        """EmailAlreadyClaimed exception contains the normalized email."""
        repo = Mock()
        repo.claim_email.return_value = False
        sender = Mock()

        service = RegistrationService(repository=repo, email_sender=sender)

        with pytest.raises(EmailAlreadyClaimed) as exc_info:
            service.register("  USER@EXAMPLE.COM  ", "password123")

        assert "user@example.com" in str(exc_info.value)

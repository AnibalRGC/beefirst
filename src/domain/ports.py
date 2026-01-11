"""
Port interfaces - Protocol definitions for infrastructure abstraction.

This module defines the interfaces (ports) that the domain requires
from infrastructure. Adapters implement these protocols.
"""

from enum import Enum
from typing import Protocol


class VerifyResult(Enum):
    """Result of verification attempt."""

    SUCCESS = "success"
    INVALID_CODE = "invalid_code"
    EXPIRED = "expired"
    LOCKED = "locked"
    NOT_FOUND = "not_found"


class RegistrationRepository(Protocol):
    """Port interface for registration persistence."""

    def claim_email(self, email: str, password_hash: str, code: str) -> bool:
        """
        Atomically claim an email address for registration.

        Args:
            email: Normalized email address
            password_hash: bcrypt hashed password
            code: 4-digit verification code

        Returns:
            True if claim successful, False if email already claimed
        """
        ...


class EmailSender(Protocol):
    """Port interface for email delivery."""

    def send_verification_code(self, email: str, code: str) -> None:
        """
        Send verification code to email address.

        Args:
            email: Recipient email address
            code: 4-digit verification code
        """
        ...

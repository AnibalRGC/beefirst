"""
Port interfaces - Protocol definitions for infrastructure abstraction.

This module defines the interfaces (ports) that the domain requires
from infrastructure. Adapters implement these protocols.
"""

from enum import Enum
from typing import Protocol


class TrustState(str, Enum):
    """
    Trust State Machine states for registration lifecycle.

    State Transitions (forward-only):
    - CLAIMED -> ACTIVE (successful verification)
    - CLAIMED -> EXPIRED (60-second TTL exceeded)
    - CLAIMED -> LOCKED (3 failed attempts)

    Terminal States:
    - ACTIVE: Registration complete, no further transitions
    - EXPIRED: Can be released for re-registration
    - LOCKED: Can be released for re-registration

    Note: Forward-only transitions are enforced at the repository level
    via SQL constraints and atomic operations.
    """

    CLAIMED = "CLAIMED"
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    LOCKED = "LOCKED"


class VerifyResult(Enum):
    """
    Result of verification attempt.

    Used by verify_and_activate() to indicate success or specific failure.
    """

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

    def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
        """
        Verify code and password, activate account if valid.

        This method performs atomic verification with row-level locking.
        Implementation uses SELECT FOR UPDATE to prevent race conditions.

        Verification checks (all must pass for SUCCESS):
        1. Email exists in CLAIMED state
        2. Code matches (using constant-time comparison)
        3. Password matches (using bcrypt constant-time comparison)
        4. Within 60-second TTL (checked via database time)
        5. Fewer than 3 failed attempts

        Return values by scenario:
        - SUCCESS: All checks pass, state transitions to ACTIVE
        - NOT_FOUND: Email not found or not in CLAIMED state
        - INVALID_CODE: Code or password mismatch (generic for security)
        - EXPIRED: TTL exceeded (created_at > 60 seconds ago)
        - LOCKED: 3+ failed attempts, state transitions to LOCKED

        Args:
            email: Normalized email address
            code: 4-digit verification code
            password: User's plaintext password (compared against hash)

        Returns:
            VerifyResult indicating success or specific failure reason
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

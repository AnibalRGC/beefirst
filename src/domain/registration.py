"""
Registration domain service - Trust State Machine implementation.

This module contains the core business logic for user registration,
implementing the Trust State Machine pattern for identity verification.

Trust State Machine (Forward-Only Transitions)
==============================================

States:
- CLAIMED: Initial state after email claim (email registered, pending verification)
- ACTIVE: Terminal state after successful verification (account activated)
- EXPIRED: Terminal state when 60-second TTL exceeded
- LOCKED: Terminal state after 3 failed verification attempts

Valid Transitions (forward-only, enforced by repository):
    CLAIMED -> ACTIVE   (successful verification)
    CLAIMED -> EXPIRED  (TTL exceeded during verification attempt)
    CLAIMED -> LOCKED   (3 failed attempts)

Invalid Transitions (never allowed):
    ACTIVE -> any       (ACTIVE is terminal)
    EXPIRED -> any      (EXPIRED is terminal)
    LOCKED -> any       (LOCKED is terminal)
    any -> CLAIMED      (no backward movement)

Note: State transition enforcement happens at the repository level via
SQL constraints and atomic operations (SELECT FOR UPDATE).
"""

import secrets
from dataclasses import dataclass

import bcrypt

from .exceptions import EmailAlreadyClaimed
from .ports import EmailSender, RegistrationRepository, VerifyResult


@dataclass
class RegistrationService:
    """
    Domain service for user registration.

    Orchestrates the registration flow: email normalization,
    password hashing, code generation, and claim persistence.
    """

    repository: RegistrationRepository
    email_sender: EmailSender

    def register(self, email: str, password: str) -> str:
        """
        Register a new user by claiming their email address.

        Args:
            email: User's email address (will be normalized)
            password: User's password (will be hashed)

        Returns:
            Normalized email address

        Raises:
            EmailAlreadyClaimed: If email is already registered
        """
        normalized_email = self._normalize_email(email)
        password_hash = self._hash_password(password)
        code = self._generate_verification_code()

        claimed = self.repository.claim_email(normalized_email, password_hash, code)
        if not claimed:
            raise EmailAlreadyClaimed(normalized_email)

        self.email_sender.send_verification_code(normalized_email, code)
        return normalized_email

    def verify_and_activate(self, email: str, code: str, password: str) -> VerifyResult:
        """
        Verify code and password, activate account if valid.

        Delegates all verification logic to the repository, which handles:
        - Atomic row-level locking (SELECT FOR UPDATE)
        - Code comparison (constant-time via secrets.compare_digest)
        - Password verification (constant-time via bcrypt)
        - TTL check (database time: NOW() - 60 seconds)
        - Attempt counting and lockout

        Args:
            email: User's email (will be normalized)
            code: 4-digit verification code
            password: User's password

        Returns:
            VerifyResult indicating success or specific failure reason
        """
        normalized_email = self._normalize_email(email)
        return self.repository.verify_and_activate(normalized_email, code, password)

    def _normalize_email(self, email: str) -> str:
        """
        Normalize email address for consistent storage and lookup.

        Applies: strip whitespace + lowercase
        """
        return email.strip().lower()

    def _generate_verification_code(self) -> str:
        """
        Generate cryptographically secure 4-digit verification code.

        Uses secrets module for cryptographic randomness (NFR-S3).
        Returns string to preserve leading zeros.
        """
        return "".join(secrets.choice("0123456789") for _ in range(4))

    def _hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt with cost factor >= 10.

        Per NFR-S1: bcrypt with cost factor >= 10.
        """
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=10)).decode()

"""
Registration domain service - Trust State Machine implementation.

This module contains the core business logic for user registration,
implementing the Trust State Machine pattern for identity verification.
"""

import secrets
from dataclasses import dataclass

import bcrypt

from .exceptions import EmailAlreadyClaimed
from .ports import EmailSender, RegistrationRepository


@dataclass
class RegistrationService:
    """
    Domain service for user registration.

    Orchestrates the registration flow: email normalization,
    password hashing, code generation, and claim persistence.
    """

    repository: RegistrationRepository
    email_sender: EmailSender

    def register(self, email: str, password: str) -> None:
        """
        Register a new user by claiming their email address.

        Args:
            email: User's email address (will be normalized)
            password: User's password (will be hashed)

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

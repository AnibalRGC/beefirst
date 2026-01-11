"""
Domain exceptions - Semantic error types for registration.

This module defines domain-specific exceptions that communicate
business rule violations without leaking infrastructure details.
"""


class RegistrationError(Exception):
    """Base class for registration domain errors."""

    pass


class EmailAlreadyClaimed(RegistrationError):
    """Email is already in CLAIMED or ACTIVE state."""

    pass


class VerificationFailed(RegistrationError):
    """Code/password mismatch, expired, or locked."""

    pass

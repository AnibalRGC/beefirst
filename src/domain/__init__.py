"""
Domain layer - Pure business logic with zero framework imports.

This package contains the core business logic for the Trust State Machine
registration system. It defines its own port interfaces for infrastructure
abstraction, ensuring true hexagonal architecture decoupling.
"""

from .exceptions import EmailAlreadyClaimed, RegistrationError, VerificationFailed
from .ports import EmailSender, RegistrationRepository, TrustState, VerifyResult
from .registration import RegistrationService

__all__ = [
    "EmailAlreadyClaimed",
    "EmailSender",
    "RegistrationError",
    "RegistrationRepository",
    "RegistrationService",
    "TrustState",
    "VerificationFailed",
    "VerifyResult",
]

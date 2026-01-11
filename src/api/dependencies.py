"""
FastAPI dependencies - Dependency injection factories.

This module provides Depends() factories for injecting
domain services and infrastructure adapters into routes.
"""

from fastapi import Depends, Request
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from psycopg_pool import ConnectionPool

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.adapters.smtp.console import ConsoleEmailSender
from src.domain.registration import RegistrationService

# Module-level singleton - ConsoleEmailSender is stateless
_email_sender = ConsoleEmailSender()


def get_pool(request: Request) -> ConnectionPool:
    """
    Get connection pool from app state.

    The pool is created during app lifespan startup and stored in app.state.
    """
    return request.app.state.pool


def get_repository(request: Request) -> PostgresRegistrationRepository:
    """Create repository with connection pool from app state."""
    pool = get_pool(request)
    return PostgresRegistrationRepository(pool)


def get_email_sender() -> ConsoleEmailSender:
    """Get console email sender (singleton)."""
    return _email_sender


def get_registration_service(request: Request) -> RegistrationService:
    """
    Create registration service with injected dependencies.

    Wires together the repository and email sender for the domain service.
    """
    repository = get_repository(request)
    email_sender = get_email_sender()
    return RegistrationService(repository=repository, email_sender=email_sender)


# HTTP BASIC AUTH security scheme for OpenAPI documentation
http_basic = HTTPBasic()


def get_basic_auth_credentials(
    credentials: HTTPBasicCredentials = Depends(http_basic),
) -> tuple[str, str]:
    """
    Extract and normalize credentials from HTTP BASIC AUTH header.

    FastAPI's HTTPBasic automatically:
    - Returns 401 for missing Authorization header
    - Returns 401 for malformed base64 encoding
    - Parses base64(email:password) format

    Args:
        credentials: HTTPBasicCredentials from FastAPI's HTTPBasic

    Returns:
        Tuple of (normalized_email, password)
        Email is stripped and lowercased for consistency.
    """
    email = credentials.username.strip().lower()
    password = credentials.password
    return email, password

"""
FastAPI dependencies - Dependency injection factories.

This module provides Depends() factories for injecting
domain services and infrastructure adapters into routes.
"""

from fastapi import Request

from src.adapters.repository.postgres import PostgresRegistrationRepository
from src.adapters.smtp.console import ConsoleEmailSender
from src.domain.registration import RegistrationService


def get_pool(request: Request):
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
    """Create console email sender."""
    return ConsoleEmailSender()


def get_registration_service(request: Request) -> RegistrationService:
    """
    Create registration service with injected dependencies.

    Wires together the repository and email sender for the domain service.
    """
    repository = get_repository(request)
    email_sender = get_email_sender()
    return RegistrationService(repository=repository, email_sender=email_sender)

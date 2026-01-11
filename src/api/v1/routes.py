"""
API v1 routes.

Defines REST endpoints for the Trust State Machine Registration API.
"""

from fastapi import APIRouter, HTTPException, status

from src.api.models import (
    ActivateRequest,
    ActivateResponse,
    ErrorResponse,
    RegisterRequest,
    RegisterResponse,
)

router = APIRouter(tags=["v1"])


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"model": ErrorResponse, "description": "Email already claimed"},
        422: {"description": "Validation error"},
    },
    summary="Register a new user",
    description="Submit email and password to begin registration. "
    "A 4-digit verification code will be sent to the provided email.",
)
async def register(request: RegisterRequest) -> RegisterResponse:
    """
    Register a new user and send verification code.

    - **email**: Valid email address to register
    - **password**: Password (minimum 8 characters)

    Returns verification code expiration time on success.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Registration not yet implemented",
    )


@router.post(
    "/activate",
    response_model=ActivateResponse,
    responses={
        401: {"model": ErrorResponse, "description": "Invalid credentials or code"},
        422: {"description": "Validation error"},
    },
    summary="Activate account with verification code",
    description="Submit the 4-digit verification code received via email "
    "along with credentials to activate the account.",
)
async def activate(request: ActivateRequest) -> ActivateResponse:
    """
    Activate account with verification code.

    - **code**: 4-digit verification code from email

    Note: Credentials are provided via HTTP BASIC AUTH header.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Activation not yet implemented",
    )

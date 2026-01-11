"""
API v1 routes.

Defines REST endpoints for the Trust State Machine Registration API.
"""

from fastapi import APIRouter, Depends, HTTPException, Request, status

from src.api.dependencies import get_basic_auth_credentials, get_registration_service
from src.api.models import (
    ActivateRequest,
    ActivateResponse,
    ErrorResponse,
    RegisterRequest,
    RegisterResponse,
)
from src.domain.exceptions import EmailAlreadyClaimed
from src.domain.ports import VerifyResult
from src.domain.registration import RegistrationService

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
async def register(
    request_data: RegisterRequest,
    request: Request,
    service: RegistrationService = Depends(get_registration_service),
) -> RegisterResponse:
    """
    Register a new user and send verification code.

    - **email**: Valid email address to register
    - **password**: Password (minimum 8 characters)

    Returns verification code expiration time on success.
    """
    try:
        normalized_email = service.register(request_data.email, request_data.password)
    except EmailAlreadyClaimed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Registration failed",
        ) from None
    return RegisterResponse(
        message="Verification code sent",
        email=normalized_email,
        expires_in_seconds=60,
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
    "along with credentials via HTTP BASIC AUTH to activate the account.",
)
async def activate(
    request_data: ActivateRequest,
    credentials: tuple[str, str] = Depends(get_basic_auth_credentials),
    service: RegistrationService = Depends(get_registration_service),
) -> ActivateResponse:
    """
    Activate account with verification code.

    - **code**: 4-digit verification code from email

    Credentials (email:password) are provided via HTTP BASIC AUTH header.
    """
    email, password = credentials

    result = service.verify_and_activate(email, request_data.code, password)

    if result == VerifyResult.SUCCESS:
        return ActivateResponse(message="Account activated", email=email)

    # All failures return identical generic error (NFR-S4, NFR-P3)
    # This prevents email enumeration, code/password differentiation, and timing attacks
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials or code",
    )

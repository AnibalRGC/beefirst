"""
API request and response models.

Pydantic models for FastAPI endpoint validation and OpenAPI schema generation.
"""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Request model for user registration."""

    email: EmailStr
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")


class RegisterResponse(BaseModel):
    """Response model for successful registration."""

    message: str
    email: str
    expires_in_seconds: int


class ActivateRequest(BaseModel):
    """Request model for account activation."""

    code: str = Field(
        ...,
        min_length=4,
        max_length=4,
        pattern=r"^\d{4}$",
        description="4-digit verification code",
    )


class ActivateResponse(BaseModel):
    """Response model for successful activation."""

    message: str
    email: str


class ErrorResponse(BaseModel):
    """Standard error response model."""

    detail: str

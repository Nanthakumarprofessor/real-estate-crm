"""
Pydantic DTOs for authentication endpoints.

LoginRequest       — POST /api/auth/login  request body
TokenResponse      — POST /api/auth/login  response
CurrentUserResponse — GET /api/auth/me     response

IMPORTANT: none of these models expose password or password_hash.
"""
from pydantic import BaseModel, EmailStr, field_validator

from src.utils.enums import UserRole


class LoginRequest(BaseModel):
    """Credentials supplied by the user on login."""
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_must_not_be_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password must not be empty")
        return v


class TokenResponse(BaseModel):
    """JWT response returned on successful login."""
    access_token: str
    token_type: str = "bearer"


class CurrentUserResponse(BaseModel):
    """
    Safe representation of the authenticated user.
    Returned by GET /api/auth/me.
    Never includes password or password_hash.
    """
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool

    model_config = {"from_attributes": True}

"""
Pydantic DTOs for User entities.

These are the API-layer representations of users.
They are distinct from the SQLAlchemy ORM model (repository/models/user.py).

SECURITY: Never expose password_hash in any response model.

Models:
  UserResponse       — full user detail returned by all admin endpoints
  UserSummary        — lightweight nested reference (e.g. lead.assigned_to)
  UserCreate         — POST /api/users request body
  UserUpdate         — PUT  /api/users/{id} request body
  UserListResponse   — paginated list wrapper for GET /api/users
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from src.utils.enums import UserRole


class UserResponse(BaseModel):
    """
    Full user representation returned by admin user-management endpoints.
    Safe to serialize — contains no password fields.
    """
    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    """
    Lightweight user reference used in nested objects
    (e.g. lead.assigned_to panel, booking.booked_by).
    """
    id: int
    name: str
    email: str
    role: UserRole

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    """
    Request body for POST /api/users (Admin only).

    The password is accepted here in plaintext and must be hashed
    by the service layer before persistence. It is never stored or
    returned in plain form.
    """
    name: str
    email: EmailStr
    password: str
    role: UserRole
    is_active: bool = True

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password must not be empty.")
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters.")
        return v


class UserUpdate(BaseModel):
    """
    Request body for PUT /api/users/{id} (Admin only).

    All fields are optional — only provided fields are updated.
    Password, if supplied, is hashed by the service layer.
    is_active may be updated here (reactivation path); the service
    enforces the last-admin rule when changing role or is_active.
    """
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip() if v else v

    @field_validator("password")
    @classmethod
    def password_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Password must not be empty.")
            if len(v) < 6:
                raise ValueError("Password must be at least 6 characters.")
        return v


class UserListResponse(BaseModel):
    """
    Paginated response envelope for GET /api/users.
    Matches the project-wide pagination convention:
        { items, total, page, size }
    """
    items: List[UserResponse]
    total: int
    page: int
    size: int

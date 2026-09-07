"""
User management router.

All endpoints are Admin-only — protected by Depends(require_admin).

Endpoints:
  GET    /api/users              — paginated user list with optional filters
  POST   /api/users              — create a new user
  GET    /api/users/{id}         — get a single user
  PUT    /api/users/{id}         — update a user
  PATCH  /api/users/{id}/deactivate — soft-deactivate a user

Authorization matrix (enforced by dependency injection, not here):
  No token   → 401   (get_current_user rejects)
  SALES role → 403   (require_admin rejects)
  ADMIN role → 200   (allowed)

Business logic lives in src/service/user_service.py.
This router handles only HTTP concerns.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import require_admin
from src.models.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import user_service
from src.utils.enums import UserRole
from src.utils.pagination import PaginationParams

router = APIRouter()


@router.get(
    "",
    response_model=UserListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all users (Admin only)",
)
def list_users(
    search: Optional[str] = Query(
        default=None,
        description="Search by name or email (case-insensitive substring)",
    ),
    role: Optional[UserRole] = Query(
        default=None,
        description="Filter by role (ADMIN or SALES)",
    ),
    is_active: Optional[bool] = Query(
        default=None,
        description="Filter by active status",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserListResponse:
    """
    GET /api/users

    Returns a paginated list of all users.
    Supports optional filtering by name/email search, role, and active status.
    """
    return user_service.list_users(
        db=db,
        pagination=pagination,
        search=search,
        role=role,
        is_active=is_active,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (Admin only)",
)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """
    POST /api/users

    Creates a new CRM user. Password is hashed before storage.
    Email is normalised to lowercase.
    Returns 409 on duplicate email.
    """
    return user_service.create_user(db=db, data=data)


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a user by ID (Admin only)",
)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """
    GET /api/users/{id}

    Returns a single user. Returns 404 if not found.
    Never returns password_hash.
    """
    return user_service.get_user(db=db, user_id=user_id)


@router.put(
    "/{user_id}",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a user (Admin only)",
)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """
    PUT /api/users/{id}

    Partially updates a user. All fields are optional.
    Enforces last-active-admin protection on role and is_active changes.
    Returns 404 if user not found, 409 on duplicate email.
    """
    return user_service.update_user(db=db, user_id=user_id, data=data)


@router.patch(
    "/{user_id}/deactivate",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user (Admin only)",
)
def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UserResponse:
    """
    PATCH /api/users/{id}/deactivate

    Soft-deactivates a user (sets is_active=false).
    Does NOT delete any associated data.
    Returns 400 if attempting to deactivate the last active admin.
    Returns 404 if user not found.
    """
    return user_service.deactivate_user(db=db, user_id=user_id)

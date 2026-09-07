"""
User management service.

Responsibilities:
  - List users (with search / role / is_active filtering + pagination)
  - Create user (with email normalisation + bcrypt hashing)
  - Get user by ID
  - Update user (partial update with last-admin protection)
  - Deactivate user (soft-delete with last-admin protection)

Business rules enforced here:
  1. Email is always normalised to lowercase before storage and lookup.
  2. Duplicate email → 409 Conflict (caught at app level and DB level).
  3. Password is NEVER stored plaintext — always hashed via security module.
  4. Passwords are NEVER logged.
  5. Last-active-admin protection:
       - Cannot deactivate the last active ADMIN.
       - Cannot change the last active ADMIN's role to SALES.
  6. Deactivation is soft (is_active=false); no data is deleted.

This layer raises AppException subclasses.
It does NOT handle HTTP — the router translates exceptions to responses.
"""
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.security import hash_password
from src.models.user import UserCreate, UserListResponse, UserResponse, UserUpdate
from src.repository.models.user import User
from src.utils.enums import UserRole
from src.utils.exceptions.custom_app_exception import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from src.utils.logger import get_logger
from src.utils.pagination import PaginationParams

logger = get_logger(__name__)

# ── Helpers ───────────────────────────────────────────────────────────────────

def _normalise_email(email: str) -> str:
    return email.strip().lower()


def _count_active_admins(db: Session) -> int:
    """Return the number of currently active ADMIN users."""
    return db.execute(
        select(func.count()).where(
            User.role == UserRole.ADMIN,
            User.is_active.is_(True),
        )
    ).scalar_one()


def _to_response(user: User) -> UserResponse:
    """Convert ORM User → safe Pydantic response. Never exposes password_hash."""
    return UserResponse.model_validate(user)


# ── Service functions ─────────────────────────────────────────────────────────

def list_users(
    db: Session,
    pagination: PaginationParams,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
) -> UserListResponse:
    """
    Return a paginated list of users with optional filters.

    Filters:
      search    — case-insensitive substring match on name OR email
      role      — exact role filter (ADMIN / SALES)
      is_active — True / False filter
    """
    stmt: Select = select(User)

    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(User.name).like(term),
                func.lower(User.email).like(term),
            )
        )

    if role is not None:
        stmt = stmt.where(User.role == role)

    if is_active is not None:
        stmt = stmt.where(User.is_active.is_(is_active))

    # Count total before applying limit/offset
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(User.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    users = db.execute(stmt).scalars().all()

    return UserListResponse(
        items=[_to_response(u) for u in users],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


def create_user(db: Session, data: UserCreate) -> UserResponse:
    """
    Create a new user.

    Normalises email to lowercase.
    Hashes the password before storing.
    Returns the created user without password information.
    Raises ConflictException on duplicate email.
    """
    normalised_email = _normalise_email(data.email)

    # Pre-check for duplicate email (clear error before hitting DB constraint)
    existing = db.execute(
        select(User).where(User.email == normalised_email)
    ).scalar_one_or_none()
    if existing:
        raise ConflictException(
            detail=f"A user with email '{normalised_email}' already exists.",
            error_code="USER_EMAIL_TAKEN",
        )

    user = User(
        name=data.name.strip(),
        email=normalised_email,
        password_hash=hash_password(data.password),  # never store plain
        role=data.role,
        is_active=data.is_active,
    )
    db.add(user)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail=f"A user with email '{normalised_email}' already exists.",
            error_code="USER_EMAIL_TAKEN",
        )

    db.commit()
    db.refresh(user)
    logger.info("User created: id=%s email=%s role=%s", user.id, user.email, user.role.value)
    return _to_response(user)


def get_user(db: Session, user_id: int) -> UserResponse:
    """
    Return a single user by ID.
    Raises NotFoundException if the user does not exist.
    """
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise NotFoundException(
            detail=f"User with id {user_id} not found.",
            error_code="USER_NOT_FOUND",
        )
    return _to_response(user)


def update_user(db: Session, user_id: int, data: UserUpdate) -> UserResponse:
    """
    Partially update a user.

    Handles:
      - Email normalisation
      - Duplicate email check
      - Password hashing (if provided)
      - Last-admin protection (role change / deactivation)
    """
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise NotFoundException(
            detail=f"User with id {user_id} not found.",
            error_code="USER_NOT_FOUND",
        )

    # ── Last-admin protection ─────────────────────────────────────────────────
    # Check before applying changes so the DB is never left in a bad state.
    is_last_admin = (
        user.role == UserRole.ADMIN
        and user.is_active
        and _count_active_admins(db) == 1
    )

    if is_last_admin:
        if data.role is not None and data.role != UserRole.ADMIN:
            raise BadRequestException(
                detail="Cannot change the role of the last active administrator.",
                error_code="LAST_ADMIN_PROTECTED",
            )
        if data.is_active is False:
            raise BadRequestException(
                detail="Cannot deactivate the last active administrator.",
                error_code="LAST_ADMIN_PROTECTED",
            )

    # ── Apply updates ─────────────────────────────────────────────────────────
    if data.name is not None:
        user.name = data.name.strip()

    if data.email is not None:
        normalised = _normalise_email(data.email)
        if normalised != user.email:
            conflict = db.execute(
                select(User).where(User.email == normalised, User.id != user_id)
            ).scalar_one_or_none()
            if conflict:
                raise ConflictException(
                    detail=f"Email '{normalised}' is already taken by another user.",
                    error_code="USER_EMAIL_TAKEN",
                )
            user.email = normalised

    if data.password is not None:
        user.password_hash = hash_password(data.password)

    if data.role is not None:
        user.role = data.role

    if data.is_active is not None:
        user.is_active = data.is_active

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail="Email already taken by another user.",
            error_code="USER_EMAIL_TAKEN",
        )

    db.commit()
    db.refresh(user)
    logger.info("User updated: id=%s", user.id)
    return _to_response(user)


def deactivate_user(db: Session, user_id: int) -> UserResponse:
    """
    Soft-deactivate a user (is_active = false).

    Does NOT delete any associated data (leads, notes, follow-ups, bookings).
    The existing authentication layer will immediately reject future requests
    from this user, even if they hold a valid JWT.

    Raises:
      NotFoundException   — user does not exist
      BadRequestException — attempting to deactivate the last active admin
    """
    user = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise NotFoundException(
            detail=f"User with id {user_id} not found.",
            error_code="USER_NOT_FOUND",
        )

    if user.is_active is False:
        # Idempotent: already inactive — return current state without error
        return _to_response(user)

    # Last-admin protection
    if user.role == UserRole.ADMIN and _count_active_admins(db) == 1:
        raise BadRequestException(
            detail="Cannot deactivate the last active administrator.",
            error_code="LAST_ADMIN_PROTECTED",
        )

    user.is_active = False
    db.commit()
    db.refresh(user)
    logger.info("User deactivated: id=%s email=%s", user.id, user.email)
    return _to_response(user)

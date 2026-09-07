"""
Security utilities: JWT encode/decode, password hashing, FastAPI dependencies.

This module is the single source of truth for:
  - Password hashing / verification (bcrypt via passlib)
  - JWT creation and decoding (python-jose)
  - FastAPI dependency functions for authentication and RBAC

Dependency hierarchy:

  get_current_user          — validates JWT, loads user from DB, checks is_active
  require_admin             — get_current_user + role == ADMIN
  require_sales_or_admin    — get_current_user + role in (ADMIN, SALES)

Every protected endpoint must use one of the above via Depends().
Role is NEVER trusted from the request body or query parameters — only from DB.

Security rules enforced here:
  - JWT secret from env (never hardcoded)
  - Expired/invalid tokens → HTTP 401
  - Inactive users → HTTP 401 (even with valid JWT)
  - Wrong role → HTTP 403
  - Passwords never logged
  - JWT tokens never logged
"""
import warnings
from datetime import datetime, timedelta, timezone
from typing import Optional

# Suppress passlib's harmless bcrypt version-detection warning
warnings.filterwarnings("ignore", message=".*error reading bcrypt version.*")

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import ExpiredSignatureError, JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.repository.database import get_db
from src.repository.models.user import User
from src.settings import get_settings
from src.utils.enums import UserRole
from src.utils.exceptions.custom_app_exception import (
    AccountInactiveException,
    ForbiddenException,
    TokenExpiredException,
    UnauthorizedException,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# ── Password hashing ──────────────────────────────────────────────────────────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the plaintext password."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.
    Returns True if they match, False otherwise.
    Never raises — a mismatch returns False.
    """
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception:
        return False


# ── JWT ───────────────────────────────────────────────────────────────────────
def create_access_token(user_id: int, role: UserRole) -> str:
    """
    Create a signed JWT access token.

    Payload contains:
      sub  — user id (as string, standard JWT claim)
      role — UserRole value (ADMIN / SALES)
      exp  — expiry timestamp (UTC)
      iat  — issued-at timestamp (UTC)

    The token is signed with JWT_SECRET_KEY using JWT_ALGORITHM.
    Neither passwords nor any sensitive data are included.
    """
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload = {
        "sub": str(user_id),
        "role": role.value,
        "exp": expire,
        "iat": now,
    }
    token = jwt.encode(
        payload,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    # NEVER log the token value
    logger.debug("Access token created for user_id=%s role=%s", user_id, role.value)
    return token


def _decode_token(token: str) -> dict:
    """
    Decode and validate a JWT.

    Raises:
      TokenExpiredException   — token has expired
      UnauthorizedException   — token is malformed / invalid signature
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except ExpiredSignatureError:
        raise TokenExpiredException()
    except JWTError:
        raise UnauthorizedException(detail="Invalid or malformed token.")


# ── HTTP Bearer extractor ─────────────────────────────────────────────────────
# auto_error=False lets us produce a clean 401 via our own exception rather
# than FastAPI's default plain-text response.
_bearer_scheme = HTTPBearer(auto_error=False)


# ── Core authentication dependency ───────────────────────────────────────────
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    FastAPI dependency — resolves the authenticated user for every request.

    Steps:
      1. Extract Bearer token from Authorization header.
      2. Decode and validate JWT (expiry, signature).
      3. Extract user_id from token subject claim.
      4. Load user from the database (source of truth — not the token).
      5. Verify user.is_active.

    Returns the ORM User object on success.

    Raises:
      UnauthorizedException   — missing/invalid/expired token, user not found
      AccountInactiveException — user exists but is deactivated

    The database check (steps 4–5) ensures that:
      - Deleted users are rejected.
      - Deactivated users are rejected even with a still-valid JWT.
      - Role is always read from the database, never trusted from the token alone.
    """
    if not credentials:
        raise UnauthorizedException(detail="Authentication required. Provide a Bearer token.")

    payload = _decode_token(credentials.credentials)

    user_id_str: Optional[str] = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedException(detail="Invalid token: missing subject claim.")

    try:
        user_id = int(user_id_str)
    except (ValueError, TypeError):
        raise UnauthorizedException(detail="Invalid token: malformed subject claim.")

    user: Optional[User] = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()

    if user is None:
        raise UnauthorizedException(detail="Authentication required.")

    if not user.is_active:
        raise AccountInactiveException()

    return user


# ── Role-based dependencies ───────────────────────────────────────────────────
def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency — requires the authenticated user to have ADMIN role.

    Raises HTTP 403 if the user is authenticated but not an Admin.
    """
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenException(detail="Admin access required.")
    return current_user


def require_sales_or_admin(current_user: User = Depends(get_current_user)) -> User:
    """
    FastAPI dependency — accepts both ADMIN and SALES roles.

    Use on endpoints that any authenticated CRM user may access.
    Business-specific ownership checks (e.g. can this Sales user access this
    particular lead) are performed in the service layer, not here.
    """
    if current_user.role not in (UserRole.ADMIN, UserRole.SALES):
        raise ForbiddenException(detail="Access denied.")
    return current_user

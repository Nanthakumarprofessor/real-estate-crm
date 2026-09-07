"""
Authentication service.

Responsibilities:
  - Find user by email (case-insensitive lookup)
  - Verify supplied password against stored bcrypt hash
  - Enforce inactive-user rejection
  - Generate JWT access token
  - Build safe CurrentUserResponse

Business rules enforced here:
  - Login always returns the same 401 message regardless of failure reason
    (email not found vs wrong password) to prevent account enumeration.
  - Inactive users are rejected at login with 401.
  - Passwords are NEVER logged.

This layer is called by auth_router.py.
It does NOT handle HTTP — it raises AppException subclasses,
which the global exception handler in src/main.py converts to HTTP responses.
"""
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core.security import create_access_token, verify_password
from src.models.auth import CurrentUserResponse, TokenResponse
from src.repository.models.user import User
from src.utils.exceptions.custom_app_exception import (
    AccountInactiveException,
    InvalidCredentialsException,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Generic message used for ALL login failures — prevents account enumeration.
_LOGIN_FAILURE_MSG = "Invalid email or password."


def login(email: str, password: str, db: Session) -> TokenResponse:
    """
    Authenticate a user and return a JWT token.

    Failure cases all return the same InvalidCredentialsException:
      - Email not found
      - Password incorrect
      - User is inactive (special subclass for clarity in tests, same HTTP 401)

    Args:
        email:    Raw email from the login request.
        password: Raw plaintext password from the login request.
        db:       SQLAlchemy session (injected via FastAPI dependency).

    Returns:
        TokenResponse containing the signed JWT and token_type.
    """
    # Normalise email to lowercase for case-insensitive lookup
    normalised_email = email.strip().lower()

    user: User | None = db.execute(
        select(User).where(User.email == normalised_email)
    ).scalar_one_or_none()

    # Use a consistent failure path to prevent timing-based account enumeration.
    # We verify a dummy hash when user is not found so response time stays similar.
    if user is None:
        # Run verify_password on a dummy value to equalise response time
        verify_password(password, "$2b$12$dummyhashpaddingtomatchrealcost000000000000000")
        logger.info("Login attempt for unknown email (not logged for security)")
        raise InvalidCredentialsException(detail=_LOGIN_FAILURE_MSG)

    if not verify_password(password, user.password_hash):
        logger.info("Failed login attempt for user_id=%s (wrong password)", user.id)
        raise InvalidCredentialsException(detail=_LOGIN_FAILURE_MSG)

    if not user.is_active:
        logger.info("Login attempt by inactive user_id=%s", user.id)
        raise AccountInactiveException(detail=_LOGIN_FAILURE_MSG)

    token = create_access_token(user_id=user.id, role=user.role)
    logger.info("User logged in: user_id=%s role=%s", user.id, user.role.value)

    return TokenResponse(access_token=token, token_type="bearer")


def get_current_user_response(user: User) -> CurrentUserResponse:
    """
    Convert an ORM User to a safe API response object.

    Called by the /api/auth/me router endpoint after the
    get_current_user dependency has already validated the token and
    confirmed the user is active.

    Never exposes password_hash.
    """
    return CurrentUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
    )

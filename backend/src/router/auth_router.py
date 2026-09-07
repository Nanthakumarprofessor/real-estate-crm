"""
Authentication router.

Endpoints:
  POST /api/auth/login   — authenticate and receive JWT
  GET  /api/auth/me      — return the currently authenticated user

All business logic lives in src/service/auth_service.py.
This router handles only HTTP concerns: request parsing, dependency injection,
response codes, and calling the service layer.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.security import get_current_user
from src.models.auth import CurrentUserResponse, LoginRequest, TokenResponse
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import auth_service

router = APIRouter()


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Login with email and password",
    description=(
        "Authenticate with valid credentials. Returns a JWT Bearer token.\n\n"
        "Use the token in the `Authorization: Bearer <token>` header on all "
        "protected endpoints.\n\n"
        "Returns HTTP 401 for invalid credentials or inactive accounts."
    ),
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    POST /api/auth/login

    Validates email/password, returns access_token on success.
    Always returns the same error message on failure to prevent
    account enumeration.
    """
    return auth_service.login(
        email=request.email,
        password=request.password,
        db=db,
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current authenticated user",
    description=(
        "Returns the profile of the currently authenticated user.\n\n"
        "Requires a valid `Authorization: Bearer <token>` header.\n\n"
        "The response never includes the password or password hash.\n\n"
        "Returns HTTP 401 if the token is missing, invalid, or expired.\n"
        "Returns HTTP 401 if the user account has been deactivated."
    ),
)
def me(
    current_user: User = Depends(get_current_user),
) -> CurrentUserResponse:
    """
    GET /api/auth/me

    Returns the authenticated user's safe profile.
    The get_current_user dependency handles all token validation and
    active-user checks before this handler is called.
    """
    return auth_service.get_current_user_response(current_user)

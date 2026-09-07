"""
Custom application exception hierarchy.

All business-logic and domain errors should raise a subclass of
`AppException`. The global exception handler in src/main.py catches
these and converts them to consistent JSON error responses.

Never raise raw SQLAlchemy errors or Python built-ins from service
layers — always wrap them in the appropriate AppException subclass.
"""
from src.utils.exceptions import http_status as status


class AppException(Exception):
    """
    Base class for all application exceptions.

    Attributes:
        status_code: HTTP status code to return to the client.
        error_code:  Machine-readable error identifier (from error_codes.py).
        detail:      Human-readable message shown to the API consumer.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_SERVER_ERROR"
    detail: str = "An unexpected error occurred."

    def __init__(
        self,
        detail: str | None = None,
        error_code: str | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.error_code = error_code or self.__class__.error_code
        super().__init__(self.detail)


# ── 400 Bad Request ───────────────────────────────────────────────────────────
class BadRequestException(AppException):
    status_code = status.HTTP_400_BAD_REQUEST
    error_code = "BAD_REQUEST"
    detail = "Bad request."


# ── 401 Unauthorized ──────────────────────────────────────────────────────────
class UnauthorizedException(AppException):
    status_code = status.HTTP_401_UNAUTHORIZED
    error_code = "AUTH_TOKEN_INVALID"
    detail = "Authentication required."


class InvalidCredentialsException(UnauthorizedException):
    error_code = "AUTH_INVALID_CREDENTIALS"
    detail = "Invalid email or password."


class TokenExpiredException(UnauthorizedException):
    error_code = "AUTH_TOKEN_EXPIRED"
    detail = "Token has expired. Please log in again."


class AccountInactiveException(UnauthorizedException):
    error_code = "AUTH_ACCOUNT_INACTIVE"
    detail = "This account has been deactivated."


# ── 403 Forbidden ─────────────────────────────────────────────────────────────
class ForbiddenException(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    error_code = "PERMISSION_DENIED"
    detail = "You do not have permission to perform this action."


# ── 404 Not Found ─────────────────────────────────────────────────────────────
class NotFoundException(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    error_code = "RESOURCE_NOT_FOUND"
    detail = "The requested resource was not found."


# ── 409 Conflict ──────────────────────────────────────────────────────────────
class ConflictException(AppException):
    status_code = status.HTTP_409_CONFLICT
    error_code = "RESOURCE_ALREADY_EXISTS"
    detail = "A conflict occurred with the current state of the resource."


class UnitAlreadyBookedException(ConflictException):
    error_code = "BOOKING_UNIT_ALREADY_BOOKED"
    detail = "This unit was just booked by someone else. Please select another unit."


class BookingNotConfirmedException(ConflictException):
    error_code = "BOOKING_NOT_CONFIRMED"
    detail = "Booking is not in CONFIRMED state and cannot be cancelled."


# ── 422 Unprocessable Entity ──────────────────────────────────────────────────
class UnprocessableEntityException(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"
    detail = "Validation failed."


# ── 500 Internal Server Error ─────────────────────────────────────────────────
class InternalServerException(AppException):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code = "INTERNAL_SERVER_ERROR"
    detail = "An unexpected internal error occurred."

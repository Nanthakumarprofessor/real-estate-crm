"""
Shared API response DTOs.

These Pydantic models form the base of all API responses.
Domain-specific response models (LeadResponse, BookingResponse, etc.)
are defined in their own files under src/models/ and may inherit from
these bases where appropriate.
"""
from typing import Any, Dict, Optional

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    """
    Generic success envelope for operations that return a simple message.
    Used for actions like deactivate, delete, etc.

    Example:
        {"message": "User deactivated successfully."}
    """
    message: str


class ErrorResponse(BaseModel):
    """
    Standard error response body.
    Matches FastAPI's default `detail` format for compatibility with
    HTTPException handling in the frontend.

    Example:
        {"detail": "Unit A-101 is already booked", "error_code": "BOOKING_UNIT_ALREADY_BOOKED"}
    """
    detail: str
    error_code: Optional[str] = None


class HealthResponse(BaseModel):
    """Response model for GET /health."""
    status: str
    database: str
    environment: str

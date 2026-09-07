"""
Pydantic DTOs for Booking entities.

Distinct from the SQLAlchemy ORM model in repository/models/booking.py.

IMPORTANT:
  booking_date is NEVER accepted from the client.
  It is always generated server-side (database DEFAULT NOW()).

Models:
  BookingCreate      — POST /api/bookings request body
  BookingResponse    — single booking response
  BookingListResponse — paginated booking list
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.utils.enums import BookingStatus


class BookingCreate(BaseModel):
    """
    Request body for POST /api/bookings.

    booking_date intentionally omitted — always server-generated.
    amount is optional (database allows NULL).
    """
    lead_id: int
    unit_id: int
    amount: Optional[Decimal] = None

    @field_validator("amount")
    @classmethod
    def amount_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("amount must be non-negative.")
        return v


class BookingResponse(BaseModel):
    """
    Full booking representation.

    Never exposes internal password fields or unrelated user data.
    booking_date is read-only (server-generated).
    """
    id: int
    lead_id: int
    unit_id: int
    booked_by: int
    booking_date: datetime
    amount: Optional[Decimal] = None
    status: BookingStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BookingListResponse(BaseModel):
    """Paginated response envelope for GET /api/bookings."""
    items: List[BookingResponse]
    total: int
    page: int
    size: int

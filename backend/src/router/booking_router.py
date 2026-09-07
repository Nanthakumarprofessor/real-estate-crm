"""
Booking router — Phase 7.

Endpoints:
  POST   /api/bookings              — create a booking (Admin or Sales)
  GET    /api/bookings              — list bookings (Admin sees all, Sales sees own)
  GET    /api/bookings/{id}         — get a booking (Admin any, Sales own)
  PATCH  /api/bookings/{id}/cancel  — cancel a booking (Admin only)

Authorization:
  POST / GET           → require_sales_or_admin (both roles)
  PATCH .../cancel     → require_admin (Admin only)

Ownership / data isolation enforced in the service layer, not here.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import require_admin, require_sales_or_admin
from src.models.booking import BookingCreate, BookingListResponse, BookingResponse
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import booking_service
from src.utils.enums import BookingStatus
from src.utils.pagination import PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=BookingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a booking",
)
def create_booking(
    data: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> BookingResponse:
    """
    POST /api/bookings

    ADMIN: can book any active lead and any available unit.
    SALES: can only book leads assigned to themselves.

    Uses SELECT FOR UPDATE to prevent concurrent double-booking.
    Returns 409 if the unit is already BOOKED.
    booking_date is server-generated and must NOT be supplied in the request.
    """
    return booking_service.create_booking(
        db=db, current_user=current_user, data=data
    )


@router.get(
    "",
    response_model=BookingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List bookings",
)
def list_bookings(
    status: Optional[BookingStatus] = Query(
        default=None,
        description="Filter by booking status (CONFIRMED / CANCELLED)",
    ),
    lead_id: Optional[int] = Query(
        default=None,
        description="Filter by lead id",
    ),
    unit_id: Optional[int] = Query(
        default=None,
        description="Filter by unit id",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> BookingListResponse:
    """
    GET /api/bookings

    ADMIN: all bookings visible.
    SALES: only their own bookings (booked_by == current user).
    Supports optional status / lead_id / unit_id filters.
    """
    return booking_service.list_bookings(
        db=db,
        current_user=current_user,
        pagination=pagination,
        status=status,
        lead_id=lead_id,
        unit_id=unit_id,
    )


@router.get(
    "/{booking_id}",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a booking by ID",
)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> BookingResponse:
    """
    GET /api/bookings/{id}

    ADMIN: can view any booking.
    SALES: can view only their own bookings; returns 403 otherwise.
    """
    return booking_service.get_booking(
        db=db, current_user=current_user, booking_id=booking_id
    )


@router.patch(
    "/{booking_id}/cancel",
    response_model=BookingResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel a booking (Admin only)",
)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BookingResponse:
    """
    PATCH /api/bookings/{id}/cancel — Admin only.

    Transitions:
      booking.status : CONFIRMED → CANCELLED
      unit.status    : BOOKED    → AVAILABLE
      lead.stage     : unchanged

    Returns 409 if the booking is already CANCELLED.
    The booking record is preserved; no DELETE is performed.
    """
    return booking_service.cancel_booking(db=db, booking_id=booking_id)

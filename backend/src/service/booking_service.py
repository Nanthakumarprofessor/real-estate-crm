"""
Booking service — Phase 7.

CRITICAL CONCURRENCY STRATEGY
──────────────────────────────
Two users may attempt to book the same unit simultaneously.

We prevent double-booking via a two-layer defence:

Layer 1 — Row-level lock (SELECT ... FOR UPDATE)
  The unit row is locked for the duration of the transaction.
  Any concurrent transaction attempting to lock the same unit will
  block until the first transaction commits or rolls back.

Layer 2 — Database partial unique index (safety net)
  uix_unit_confirmed_booking on bookings(unit_id) WHERE status='CONFIRMED'
  If SELECT FOR UPDATE somehow fails to prevent a race (e.g. in a
  multi-process deployment without connection pooling), the DB constraint
  fires and raises IntegrityError, which we catch and convert to 409.

Transaction flow for booking creation:
  BEGIN (implicit — autocommit=False)
  ┌─ SELECT unit FOR UPDATE          ← acquires row lock
  │  CHECK unit.status == AVAILABLE  ← reject if already BOOKED
  │  CHECK lead existence/activity
  │  CHECK Sales ownership if SALES user
  │  INSERT booking (status=CONFIRMED)
  │  UPDATE unit.status = BOOKED
  │  UPDATE lead.stage = BOOKED
  └─ COMMIT                          ← releases lock

Transaction flow for cancellation:
  BEGIN
  ┌─ SELECT booking FOR UPDATE       ← locks booking row
  │  CHECK booking.status == CONFIRMED
  │  SELECT unit FOR UPDATE          ← locks unit row
  │  UPDATE booking.status = CANCELLED
  │  UPDATE unit.status = AVAILABLE
  └─ COMMIT

Authorization rules:
  ADMIN  — can book any active lead / any available unit
  SALES  — can only book leads assigned to themselves
  ADMIN  — can cancel any CONFIRMED booking
  SALES  — cannot cancel (403 enforced at router level)
  ADMIN  — can list/get all bookings
  SALES  — can list/get only bookings where booked_by == current_user.id
"""
from decimal import Decimal
from typing import Optional

from sqlalchemy import Select, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.booking import BookingCreate, BookingListResponse, BookingResponse
from src.repository.models.booking import Booking
from src.repository.models.lead import Lead
from src.repository.models.unit import Unit
from src.utils.enums import BookingStatus, LeadStage, UnitStatus, UserRole
from src.utils.exceptions.custom_app_exception import (
    BadRequestException,
    BookingNotConfirmedException,
    ForbiddenException,
    NotFoundException,
    UnitAlreadyBookedException,
)
from src.utils.logger import get_logger
from src.utils.pagination import PaginationParams
from src.repository.models.user import User

logger = get_logger(__name__)


# ── Converters ────────────────────────────────────────────────────────────────

def _to_response(booking: Booking) -> BookingResponse:
    return BookingResponse.model_validate(booking)


# ── Lookups ───────────────────────────────────────────────────────────────────

def _get_booking_or_404(db: Session, booking_id: int) -> Booking:
    booking: Optional[Booking] = db.execute(
        select(Booking).where(Booking.id == booking_id)
    ).scalar_one_or_none()
    if booking is None:
        raise NotFoundException(
            detail=f"Booking with id {booking_id} not found.",
            error_code="BOOKING_NOT_FOUND",
        )
    return booking


def _get_lead_or_404(db: Session, lead_id: int) -> Lead:
    lead: Optional[Lead] = db.execute(
        select(Lead).where(Lead.id == lead_id)
    ).scalar_one_or_none()
    if lead is None:
        raise NotFoundException(
            detail=f"Lead with id {lead_id} not found.",
            error_code="LEAD_NOT_FOUND",
        )
    return lead


# ═════════════════════════════════════════════════════════════════════════════
# CREATE BOOKING
# ═════════════════════════════════════════════════════════════════════════════

def create_booking(
    db: Session,
    current_user: User,
    data: BookingCreate,
) -> BookingResponse:
    """
    Create a confirmed booking.

    Uses SELECT FOR UPDATE on the unit row to prevent concurrent double-booking.
    All mutations (booking insert, unit status, lead stage) happen in a single
    transaction — a failure in any step rolls everything back.

    ADMIN: can book any active lead and any available unit.
    SALES: can book only leads assigned to themselves.
    """
    # ── Validate lead ─────────────────────────────────────────────────────────
    lead = _get_lead_or_404(db, data.lead_id)

    if not lead.is_active:
        raise BadRequestException(
            detail=f"Lead with id {data.lead_id} is inactive and cannot be booked.",
            error_code="LEAD_INACTIVE",
        )

    if current_user.role == UserRole.SALES and lead.assigned_to != current_user.id:
        raise ForbiddenException(
            detail="You can only book leads assigned to yourself.",
            error_code="LEAD_ACCESS_DENIED",
        )

    # ── Lock and validate unit (SELECT FOR UPDATE) ────────────────────────────
    # with_for_update() acquires a row-level exclusive lock.
    # Concurrent transactions trying to lock the same row will block here until
    # this transaction commits or rolls back.
    unit: Optional[Unit] = db.execute(
        select(Unit).where(Unit.id == data.unit_id).with_for_update()
    ).scalar_one_or_none()

    if unit is None:
        raise NotFoundException(
            detail=f"Unit with id {data.unit_id} not found.",
            error_code="UNIT_NOT_FOUND",
        )

    if unit.status != UnitStatus.AVAILABLE:
        raise UnitAlreadyBookedException(
            detail="This unit is not available for booking.",
        )

    # ── Create booking ────────────────────────────────────────────────────────
    booking = Booking(
        lead_id=data.lead_id,
        unit_id=data.unit_id,
        booked_by=current_user.id,
        amount=data.amount,
        status=BookingStatus.CONFIRMED,
        # booking_date uses database server_default (NOW()) — not set here
    )
    db.add(booking)

    # ── Update unit status ────────────────────────────────────────────────────
    unit.status = UnitStatus.BOOKED

    # ── Update lead stage ─────────────────────────────────────────────────────
    lead.stage = LeadStage.BOOKED

    # ── Commit everything atomically ──────────────────────────────────────────
    try:
        db.flush()   # sends SQL to DB within the transaction; lock is held
        db.commit()
    except IntegrityError:
        db.rollback()
        # The partial unique index fired — another transaction booked this unit
        # in the instant between our SELECT FOR UPDATE and INSERT.
        raise UnitAlreadyBookedException(
            detail="This unit has already been booked.",
        )

    db.refresh(booking)
    logger.info(
        "Booking created: id=%s unit_id=%s lead_id=%s by user_id=%s",
        booking.id, data.unit_id, data.lead_id, current_user.id,
    )
    return _to_response(booking)


# ═════════════════════════════════════════════════════════════════════════════
# LIST BOOKINGS
# ═════════════════════════════════════════════════════════════════════════════

def list_bookings(
    db: Session,
    current_user: User,
    pagination: PaginationParams,
    status: Optional[BookingStatus] = None,
    lead_id: Optional[int] = None,
    unit_id: Optional[int] = None,
) -> BookingListResponse:
    """
    Return paginated bookings.

    ADMIN: all bookings visible.
    SALES: only bookings where booked_by == current_user.id (DB-level scope).
    """
    stmt: Select = select(Booking)

    # Ownership scope — enforced at query level
    if current_user.role == UserRole.SALES:
        stmt = stmt.where(Booking.booked_by == current_user.id)

    if status is not None:
        stmt = stmt.where(Booking.status == status)
    if lead_id is not None:
        stmt = stmt.where(Booking.lead_id == lead_id)
    if unit_id is not None:
        stmt = stmt.where(Booking.unit_id == unit_id)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Booking.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    bookings = db.execute(stmt).scalars().all()

    return BookingListResponse(
        items=[_to_response(b) for b in bookings],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


# ═════════════════════════════════════════════════════════════════════════════
# GET BOOKING
# ═════════════════════════════════════════════════════════════════════════════

def get_booking(
    db: Session,
    current_user: User,
    booking_id: int,
) -> BookingResponse:
    """
    Return a single booking.

    ADMIN: can view any booking.
    SALES: can view only their own bookings (booked_by == current_user.id).
    """
    booking = _get_booking_or_404(db, booking_id)

    if current_user.role == UserRole.SALES and booking.booked_by != current_user.id:
        raise ForbiddenException(
            detail="You do not have access to this booking.",
            error_code="BOOKING_ACCESS_DENIED",
        )

    return _to_response(booking)


# ═════════════════════════════════════════════════════════════════════════════
# CANCEL BOOKING
# ═════════════════════════════════════════════════════════════════════════════

def cancel_booking(
    db: Session,
    booking_id: int,
) -> BookingResponse:
    """
    Cancel a CONFIRMED booking (Admin only — enforced at router level).

    Uses SELECT FOR UPDATE on both the booking and the unit to prevent
    concurrent cancellation races.

    State transitions:
      booking.status : CONFIRMED → CANCELLED
      unit.status    : BOOKED    → AVAILABLE
      lead.stage     : unchanged (historical record preserved)

    Raises BookingNotConfirmedException if already CANCELLED.
    """
    # Lock booking row
    booking: Optional[Booking] = db.execute(
        select(Booking).where(Booking.id == booking_id).with_for_update()
    ).scalar_one_or_none()

    if booking is None:
        raise NotFoundException(
            detail=f"Booking with id {booking_id} not found.",
            error_code="BOOKING_NOT_FOUND",
        )

    if booking.status != BookingStatus.CONFIRMED:
        raise BookingNotConfirmedException()

    # Lock unit row
    unit: Optional[Unit] = db.execute(
        select(Unit).where(Unit.id == booking.unit_id).with_for_update()
    ).scalar_one_or_none()

    # Update states
    booking.status = BookingStatus.CANCELLED
    if unit is not None:
        unit.status = UnitStatus.AVAILABLE

    # Lead stage is intentionally NOT reverted

    db.commit()
    db.refresh(booking)
    logger.info("Booking cancelled: id=%s unit_id=%s", booking.id, booking.unit_id)
    return _to_response(booking)

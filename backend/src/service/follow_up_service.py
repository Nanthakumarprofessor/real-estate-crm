"""
Follow-up service.

Business rules enforced here:
  - follow_up_at cannot be in the past when CREATING a new follow-up.
  - ADMIN can create/update/list follow-ups for any lead.
  - SALES can create/update follow-ups only for their assigned leads.
  - GET /api/follow-ups lists all follow-ups for the current user's scope:
      Admin → all follow-ups
      Sales → follow-ups for leads assigned to themselves
        (i.e. follow_up.lead.assigned_to == current_user.id)
  - Status filter (PENDING / COMPLETED / CANCELLED) is supported.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.lead import (
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpResponse,
    FollowUpUpdate,
)
from src.repository.models.follow_up import FollowUp
from src.repository.models.lead import Lead
from src.repository.models.user import User
from src.utils.enums import FollowUpStatus, UserRole
from src.utils.exceptions.custom_app_exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from src.utils.logger import get_logger
from src.utils.pagination import PaginationParams
from sqlalchemy import func

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(fu: FollowUp) -> FollowUpResponse:
    return FollowUpResponse.model_validate(fu)


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


def _assert_sales_owns_lead(current_user: User, lead: Lead) -> None:
    if current_user.role == UserRole.SALES and lead.assigned_to != current_user.id:
        raise ForbiddenException(
            detail="You do not have access to this lead.",
            error_code="LEAD_ACCESS_DENIED",
        )


def _get_follow_up_or_404(db: Session, follow_up_id: int) -> FollowUp:
    fu: Optional[FollowUp] = db.execute(
        select(FollowUp).where(FollowUp.id == follow_up_id)
    ).scalar_one_or_none()
    if fu is None:
        raise NotFoundException(
            detail=f"Follow-up with id {follow_up_id} not found.",
            error_code="FOLLOW_UP_NOT_FOUND",
        )
    return fu


def _assert_sales_owns_follow_up(db: Session, current_user: User, fu: FollowUp) -> None:
    """
    For Sales users: verify the follow-up's lead is assigned to them.
    Loads the lead to check ownership.
    """
    if current_user.role == UserRole.SALES:
        lead: Optional[Lead] = db.execute(
            select(Lead).where(Lead.id == fu.lead_id)
        ).scalar_one_or_none()
        if lead is None or lead.assigned_to != current_user.id:
            raise ForbiddenException(
                detail="You do not have access to this follow-up.",
                error_code="FOLLOW_UP_ACCESS_DENIED",
            )


# ── Service functions ─────────────────────────────────────────────────────────

def create_follow_up(
    db: Session,
    current_user: User,
    lead_id: int,
    data: FollowUpCreate,
) -> FollowUpResponse:
    """
    Create a follow-up for a lead.

    Validates:
      - Lead exists and is accessible to current_user.
      - follow_up_at is not in the past (UTC comparison).

    The follow-up is always assigned to the current_user.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    # Reject past dates — compare in UTC
    now_utc = datetime.now(timezone.utc)
    fu_at = data.follow_up_at
    # Normalize to UTC for comparison (handle naive datetimes gracefully)
    if fu_at.tzinfo is None:
        fu_at = fu_at.replace(tzinfo=timezone.utc)
    if fu_at <= now_utc:
        raise BadRequestException(
            detail="follow_up_at must be a future date/time.",
            error_code="FOLLOW_UP_PAST_DATE",
        )

    fu = FollowUp(
        lead_id=lead_id,
        assigned_to=current_user.id,
        follow_up_at=fu_at,
        notes=data.notes,
        status=data.status,
    )
    db.add(fu)
    db.commit()
    db.refresh(fu)
    logger.info("Follow-up created: id=%s lead_id=%s by user_id=%s", fu.id, lead_id, current_user.id)
    return _to_response(fu)


def list_follow_ups_for_lead(
    db: Session,
    current_user: User,
    lead_id: int,
    status: Optional[FollowUpStatus] = None,
) -> FollowUpListResponse:
    """
    Return all follow-ups for a specific lead.

    Verifies lead access before returning.
    Optional status filter.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    stmt = select(FollowUp).where(FollowUp.lead_id == lead_id)
    if status is not None:
        stmt = stmt.where(FollowUp.status == status)
    stmt = stmt.order_by(FollowUp.follow_up_at.asc())

    follow_ups = db.execute(stmt).scalars().all()
    items = [_to_response(fu) for fu in follow_ups]

    return FollowUpListResponse(
        items=items,
        total=len(items),
        page=1,
        size=len(items) if items else 10,
    )


def list_all_follow_ups(
    db: Session,
    current_user: User,
    pagination: PaginationParams,
    status: Optional[FollowUpStatus] = None,
) -> FollowUpListResponse:
    """
    Return all follow-ups visible to the current user (paginated).

    ADMIN: all follow-ups in the system.
    SALES: follow-ups where the related lead is assigned to themselves.
           Implemented as a JOIN with leads to scope at the DB level.

    Supports optional status filter.
    """
    stmt = select(FollowUp)

    if current_user.role == UserRole.SALES:
        # Join to leads table and filter by assigned_to — DB-level isolation
        stmt = stmt.join(Lead, FollowUp.lead_id == Lead.id).where(
            Lead.assigned_to == current_user.id
        )

    if status is not None:
        stmt = stmt.where(FollowUp.status == status)

    # Count before pagination
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(FollowUp.follow_up_at.asc()).offset(pagination.offset).limit(pagination.limit)
    follow_ups = db.execute(stmt).scalars().all()

    return FollowUpListResponse(
        items=[_to_response(fu) for fu in follow_ups],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


def update_follow_up(
    db: Session,
    current_user: User,
    follow_up_id: int,
    data: FollowUpUpdate,
) -> FollowUpResponse:
    """
    Partially update a follow-up.

    ADMIN: can update any follow-up.
    SALES: can update only follow-ups for their assigned leads.

    If follow_up_at is being changed, it must not be in the past.
    """
    fu = _get_follow_up_or_404(db, follow_up_id)
    _assert_sales_owns_follow_up(db, current_user, fu)

    if data.follow_up_at is not None:
        fu_at = data.follow_up_at
        if fu_at.tzinfo is None:
            fu_at = fu_at.replace(tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        if fu_at <= now_utc:
            raise BadRequestException(
                detail="follow_up_at must be a future date/time.",
                error_code="FOLLOW_UP_PAST_DATE",
            )
        fu.follow_up_at = fu_at

    if data.notes is not None:
        fu.notes = data.notes

    if data.status is not None:
        fu.status = data.status

    db.commit()
    db.refresh(fu)
    logger.info("Follow-up updated: id=%s by user_id=%s", fu.id, current_user.id)
    return _to_response(fu)

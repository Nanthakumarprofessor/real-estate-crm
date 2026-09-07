"""
Dashboard service — Phase 8.

All statistics are computed using aggregate SQL queries.
No full table scans followed by Python-side counting.

Role scoping:
  ADMIN — system-wide view of all entities.
  SALES — scoped to their own data:
    leads       WHERE assigned_to = current_user.id
    follow_ups  WHERE lead.assigned_to = current_user.id  (JOIN on leads)
    bookings    WHERE booked_by = current_user.id
    properties  always global (Sales has read-only inventory access)

Query strategy:
  leads by_stage : single GROUP BY query → dict, zeros filled for missing stages
  follow_ups     : two filtered COUNT queries (upcoming / overdue)
  properties     : three scalar COUNT queries (total / available / booked)
  bookings       : two scalar COUNT queries (confirmed / cancelled)

The idx_followups_assignee_status composite index on (assigned_to, status, follow_up_at)
is used by the follow-up queries for efficient filtering.
"""
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from src.models.dashboard import (
    BookingStatistics,
    DashboardSummaryResponse,
    FollowUpStatistics,
    LeadStatistics,
    PropertyStatistics,
)
from src.repository.models.booking import Booking
from src.repository.models.follow_up import FollowUp
from src.repository.models.lead import Lead
from src.repository.models.unit import Unit
from src.repository.models.user import User
from src.utils.enums import (
    BookingStatus,
    FollowUpStatus,
    LeadStage,
    UnitStatus,
    UserRole,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


def get_summary(db: Session, current_user: User) -> DashboardSummaryResponse:
    """
    Build and return the full dashboard summary for the current user.

    All data is fetched via aggregate SQL queries — no Python-side counting.
    """
    is_admin = current_user.role == UserRole.ADMIN
    user_id = current_user.id

    return DashboardSummaryResponse(
        leads=_lead_statistics(db, is_admin, user_id),
        follow_ups=_follow_up_statistics(db, is_admin, user_id),
        properties=_property_statistics(db),
        bookings=_booking_statistics(db, is_admin, user_id),
    )


# ── Lead statistics ───────────────────────────────────────────────────────────

def _lead_statistics(db: Session, is_admin: bool, user_id: int) -> LeadStatistics:
    """
    Count active leads grouped by stage.

    Uses a single GROUP BY query.
    All LeadStage values are always present in the result dict (zeros for missing).

    Admin: all active leads.
    Sales: only leads assigned to current user.
    """
    stmt = (
        select(Lead.stage, func.count().label("cnt"))
        .where(Lead.is_active.is_(True))
        .group_by(Lead.stage)
    )
    if not is_admin:
        stmt = stmt.where(Lead.assigned_to == user_id)

    rows = db.execute(stmt).all()

    # Build a dict with all stages present, defaulting to 0
    by_stage: dict[str, int] = {stage.value: 0 for stage in LeadStage}
    total = 0
    for stage, cnt in rows:
        by_stage[stage.value] = cnt
        total += cnt

    return LeadStatistics(total=total, by_stage=by_stage)


# ── Follow-up statistics ──────────────────────────────────────────────────────

def _follow_up_statistics(db: Session, is_admin: bool, user_id: int) -> FollowUpStatistics:
    """
    Count PENDING follow-ups split into upcoming (future) and overdue (past).

    Admin: all follow-ups.
    Sales: only follow-ups whose lead is assigned to the current user.
           Uses a JOIN on leads rather than follow_ups.assigned_to so that
           follow-ups created by any user for a Sales-owned lead are included.

    Uses two scalar COUNT queries — both hit the composite index
    idx_followups_assignee_status(assigned_to, status, follow_up_at) for Admin
    and the leads join index for Sales.
    """
    now = datetime.now(timezone.utc)

    base = select(func.count()).select_from(FollowUp).where(
        FollowUp.status == FollowUpStatus.PENDING
    )
    if not is_admin:
        base = base.join(Lead, FollowUp.lead_id == Lead.id).where(
            Lead.assigned_to == user_id
        )

    upcoming: int = db.execute(
        base.where(FollowUp.follow_up_at >= now)
    ).scalar_one()

    overdue: int = db.execute(
        base.where(FollowUp.follow_up_at < now)
    ).scalar_one()

    return FollowUpStatistics(upcoming=upcoming, overdue=overdue)


# ── Property statistics ───────────────────────────────────────────────────────

def _property_statistics(db: Session) -> PropertyStatistics:
    """
    System-wide unit counts (both roles see the same property inventory).

    Uses a single query with conditional aggregation to avoid multiple round-trips.
    """
    row = db.execute(
        select(
            func.count().label("total"),
            func.count(
                case((Unit.status == UnitStatus.AVAILABLE, 1))
            ).label("available"),
            func.count(
                case((Unit.status == UnitStatus.BOOKED, 1))
            ).label("booked"),
        )
    ).one()

    return PropertyStatistics(
        total_units=row.total,
        available_units=row.available,
        booked_units=row.booked,
    )


# ── Booking statistics ────────────────────────────────────────────────────────

def _booking_statistics(db: Session, is_admin: bool, user_id: int) -> BookingStatistics:
    """
    Count bookings by status.

    Admin: all bookings.
    Sales: only bookings where booked_by == current_user.id.

    Uses a single query with conditional aggregation.
    """
    stmt = select(
        func.count(
            case((Booking.status == BookingStatus.CONFIRMED, 1))
        ).label("confirmed"),
        func.count(
            case((Booking.status == BookingStatus.CANCELLED, 1))
        ).label("cancelled"),
    )
    if not is_admin:
        stmt = stmt.where(Booking.booked_by == user_id)

    row = db.execute(stmt).one()

    return BookingStatistics(confirmed=row.confirmed, cancelled=row.cancelled)

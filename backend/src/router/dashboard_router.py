"""
Dashboard router — Phase 8.

Endpoints:
  GET /api/dashboard/summary — returns aggregated CRM statistics

Authorization:
  Both ADMIN and SALES roles are permitted.
  Data scoping (whose leads/follow-ups/bookings are counted) is enforced
  entirely within the service layer, not here.

  Uses get_current_user so that 401 is returned for unauthenticated requests.
  Both roles reach the service; the service applies the appropriate scope.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.core.security import get_current_user
from src.models.dashboard import DashboardSummaryResponse
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import dashboard_service

router = APIRouter()


@router.get(
    "/summary",
    response_model=DashboardSummaryResponse,
    summary="Get dashboard summary",
)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardSummaryResponse:
    """
    GET /api/dashboard/summary

    Returns aggregated CRM statistics for the authenticated user.

    ADMIN: system-wide view (all leads, follow-ups, bookings).
    SALES: scoped to own data (leads assigned to them, their bookings,
           follow-ups for their leads). Property stats are always global.

    All statistics use aggregate SQL queries — no Python-side counting.
    """
    return dashboard_service.get_summary(db=db, current_user=current_user)

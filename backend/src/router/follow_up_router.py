"""
Follow-up router — global follow-up endpoints (not nested under a lead).

Endpoints:
  GET /api/follow-ups          — list all follow-ups visible to current user
  PUT /api/follow-ups/{id}     — update a follow-up

Authorization:
  All endpoints require an authenticated user (ADMIN or SALES).
  ADMIN sees all follow-ups.
  SALES sees only follow-ups for leads assigned to themselves.
  Ownership checks are enforced in the service layer.
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import require_sales_or_admin
from src.models.lead import FollowUpListResponse, FollowUpResponse, FollowUpUpdate
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import follow_up_service
from src.utils.enums import FollowUpStatus
from src.utils.pagination import PaginationParams

router = APIRouter()


@router.get(
    "",
    response_model=FollowUpListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all follow-ups",
)
def list_all_follow_ups(
    status: Optional[FollowUpStatus] = Query(
        default=None,
        description="Filter by status (PENDING / COMPLETED / CANCELLED)",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> FollowUpListResponse:
    """
    GET /api/follow-ups

    ADMIN: all follow-ups in the system.
    SALES: follow-ups for leads assigned to themselves only.

    Supports optional ?status=PENDING / COMPLETED / CANCELLED filter.
    Returns paginated results.
    """
    return follow_up_service.list_all_follow_ups(
        db=db,
        current_user=current_user,
        pagination=pagination,
        status=status,
    )


@router.put(
    "/{follow_up_id}",
    response_model=FollowUpResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a follow-up",
)
def update_follow_up(
    follow_up_id: int,
    data: FollowUpUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> FollowUpResponse:
    """
    PUT /api/follow-ups/{follow_up_id}

    ADMIN: can update any follow-up.
    SALES: can update only follow-ups for their assigned leads.
    If follow_up_at is provided it must be a future datetime.
    """
    return follow_up_service.update_follow_up(
        db=db,
        current_user=current_user,
        follow_up_id=follow_up_id,
        data=data,
    )

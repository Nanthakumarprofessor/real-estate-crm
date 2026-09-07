"""
Lead management router.

Endpoints:
  POST   /api/leads                              — create a lead
  GET    /api/leads                              — list leads (paginated + filtered)
  GET    /api/leads/{lead_id}                    — get a single lead
  PUT    /api/leads/{lead_id}                    — update a lead
  DELETE /api/leads/{lead_id}                    — soft-delete a lead (Admin only)

  POST   /api/leads/{lead_id}/notes              — add a note to a lead
  GET    /api/leads/{lead_id}/notes              — list notes for a lead
  DELETE /api/leads/{lead_id}/notes/{note_id}    — delete a note

  POST   /api/leads/{lead_id}/follow-ups         — create a follow-up
  GET    /api/leads/{lead_id}/follow-ups         — list follow-ups for a lead

Authorization:
  All endpoints require an authenticated user (ADMIN or SALES).
  Business-level ownership checks (e.g. Sales can only see their own leads)
  are enforced in the service layer, not here.
  DELETE /api/leads/{lead_id} is Admin-only (require_admin dependency).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import get_current_user, require_admin, require_sales_or_admin
from src.models.api_response_dto import SuccessResponse
from src.models.lead import (
    FollowUpCreate,
    FollowUpListResponse,
    FollowUpResponse,
    LeadCreate,
    LeadListResponse,
    LeadNoteCreate,
    LeadNoteListResponse,
    LeadNoteResponse,
    LeadResponse,
    LeadUpdate,
)
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import follow_up_service, lead_note_service, lead_service
from src.utils.enums import FollowUpStatus, LeadStage
from src.utils.pagination import PaginationParams

router = APIRouter()


# ═════════════════════════════════════════════════════════════════════════════
# Lead CRUD
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new lead",
)
def create_lead(
    data: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadResponse:
    """
    POST /api/leads

    ADMIN: can create a lead and optionally assign it to any active user.
    SALES: can create a lead; assigned_to is automatically set to themselves.
    """
    return lead_service.create_lead(db=db, current_user=current_user, data=data)


@router.get(
    "",
    response_model=LeadListResponse,
    status_code=status.HTTP_200_OK,
    summary="List leads",
)
def list_leads(
    search: Optional[str] = Query(
        default=None,
        description="Search by name, email, or phone (case-insensitive substring)",
    ),
    stage: Optional[LeadStage] = Query(
        default=None,
        description="Filter by pipeline stage",
    ),
    assigned_to: Optional[int] = Query(
        default=None,
        description="Filter by assigned user id (Admin only)",
    ),
    is_active: Optional[bool] = Query(
        default=None,
        description="Filter by active status (defaults to active-only if omitted)",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadListResponse:
    """
    GET /api/leads

    ADMIN: all leads visible. Supports assigned_to filter.
    SALES: only leads assigned to themselves. assigned_to filter ignored.
    Default behaviour (no is_active param): returns active leads only.
    """
    return lead_service.list_leads(
        db=db,
        current_user=current_user,
        pagination=pagination,
        search=search,
        stage=stage,
        assigned_to=assigned_to,
        is_active=is_active,
    )


@router.get(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a lead by ID",
)
def get_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadResponse:
    """
    GET /api/leads/{lead_id}

    ADMIN: can retrieve any lead.
    SALES: can retrieve only leads assigned to themselves. Returns 403 otherwise.
    """
    return lead_service.get_lead(db=db, current_user=current_user, lead_id=lead_id)


@router.put(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a lead",
)
def update_lead(
    lead_id: int,
    data: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadResponse:
    """
    PUT /api/leads/{lead_id}

    ADMIN: can update all fields including assigned_to.
    SALES: can update their assigned leads; assigned_to field is ignored.
    """
    return lead_service.update_lead(
        db=db, current_user=current_user, lead_id=lead_id, data=data
    )


@router.delete(
    "/{lead_id}",
    response_model=LeadResponse,
    status_code=status.HTTP_200_OK,
    summary="Soft-delete a lead (Admin only)",
)
def delete_lead(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
) -> LeadResponse:
    """
    DELETE /api/leads/{lead_id}

    Sets is_active=False. Does not destroy notes, follow-ups, or bookings.
    Admin only.
    """
    return lead_service.delete_lead(
        db=db, current_user=current_user, lead_id=lead_id
    )


# ═════════════════════════════════════════════════════════════════════════════
# Lead Notes
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{lead_id}/notes",
    response_model=LeadNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a note to a lead",
)
def create_note(
    lead_id: int,
    data: LeadNoteCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadNoteResponse:
    """
    POST /api/leads/{lead_id}/notes

    ADMIN: can add a note to any lead.
    SALES: can add a note only to their assigned leads.
    Notes are immutable once created.
    """
    return lead_note_service.create_note(
        db=db, current_user=current_user, lead_id=lead_id, data=data
    )


@router.get(
    "/{lead_id}/notes",
    response_model=LeadNoteListResponse,
    status_code=status.HTTP_200_OK,
    summary="List notes for a lead",
)
def list_notes(
    lead_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> LeadNoteListResponse:
    """
    GET /api/leads/{lead_id}/notes

    ADMIN: can view notes for any lead.
    SALES: can view notes only for their assigned leads.
    """
    return lead_note_service.list_notes(
        db=db, current_user=current_user, lead_id=lead_id
    )


@router.delete(
    "/{lead_id}/notes/{note_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a note",
)
def delete_note(
    lead_id: int,
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> SuccessResponse:
    """
    DELETE /api/leads/{lead_id}/notes/{note_id}

    ADMIN: can delete any note.
    SALES: can delete only their own notes on their assigned leads.
    """
    lead_note_service.delete_note(
        db=db, current_user=current_user, lead_id=lead_id, note_id=note_id
    )
    return SuccessResponse(message="Note deleted successfully.")


# ═════════════════════════════════════════════════════════════════════════════
# Follow-ups (nested under leads)
# ═════════════════════════════════════════════════════════════════════════════

@router.post(
    "/{lead_id}/follow-ups",
    response_model=FollowUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a follow-up for a lead",
)
def create_follow_up(
    lead_id: int,
    data: FollowUpCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> FollowUpResponse:
    """
    POST /api/leads/{lead_id}/follow-ups

    ADMIN: can create follow-ups for any lead.
    SALES: can create follow-ups only for their assigned leads.
    follow_up_at must be a future datetime.
    """
    return follow_up_service.create_follow_up(
        db=db, current_user=current_user, lead_id=lead_id, data=data
    )


@router.get(
    "/{lead_id}/follow-ups",
    response_model=FollowUpListResponse,
    status_code=status.HTTP_200_OK,
    summary="List follow-ups for a lead",
)
def list_follow_ups_for_lead(
    lead_id: int,
    status: Optional[FollowUpStatus] = Query(
        default=None,
        description="Filter by follow-up status",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_or_admin),
) -> FollowUpListResponse:
    """
    GET /api/leads/{lead_id}/follow-ups

    ADMIN: all follow-ups for the lead.
    SALES: follow-ups only for their assigned leads.
    Supports optional status filter.
    """
    return follow_up_service.list_follow_ups_for_lead(
        db=db, current_user=current_user, lead_id=lead_id, status=status
    )

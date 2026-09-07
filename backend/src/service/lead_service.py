"""
Lead management service.

Responsibilities:
  - List leads (with search / stage / assigned_to / is_active filtering + pagination)
  - Create lead
  - Get lead by ID
  - Update lead (partial update)
  - Soft-delete lead (is_active = False)

Authorization rules enforced here (not in router):
  ADMIN:
    - Can see all leads (active and inactive via filter)
    - Can create leads and assign them to any user
    - Can update any lead including assignment
    - Can soft-delete any lead

  SALES:
    - Can create leads (assigned_to is set to themselves automatically)
    - Can only see leads assigned to themselves
    - Can only update leads assigned to themselves
    - Cannot change assigned_to (field is silently ignored)
    - Cannot soft-delete (403 from router dependency)

Data isolation rule (critical):
  Sales queries are scoped at the DB query level — Lead.assigned_to == current_user.id.
  We never fetch all leads and filter in Python.

Business rules:
  - Soft delete: is_active = False (never physical delete)
  - assigned_to must be a valid SALES or ADMIN user when provided
  - Inactive leads are excluded from default listing (show_inactive=False)
"""
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from src.models.lead import (
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    LeadUpdate,
)
from src.repository.models.lead import Lead
from src.repository.models.user import User
from src.utils.enums import LeadStage, UserRole
from src.utils.exceptions.custom_app_exception import (
    BadRequestException,
    ForbiddenException,
    NotFoundException,
)
from src.utils.logger import get_logger
from src.utils.pagination import PaginationParams

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(lead: Lead) -> LeadResponse:
    """Convert ORM Lead → Pydantic response."""
    return LeadResponse.model_validate(lead)


def _assert_assignee_exists(db: Session, user_id: int) -> None:
    """
    Verify that the target assignee exists and is active.
    Raises BadRequestException if not found or inactive.
    """
    user: Optional[User] = db.execute(
        select(User).where(User.id == user_id)
    ).scalar_one_or_none()
    if user is None or not user.is_active:
        raise BadRequestException(
            detail=f"Assignee user with id {user_id} does not exist or is inactive.",
            error_code="LEAD_INVALID_ASSIGNEE",
        )


def _get_lead_or_404(db: Session, lead_id: int) -> Lead:
    """Return the Lead ORM object or raise NotFoundException."""
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
    """
    For Sales users: verify the lead is assigned to them.
    Raises ForbiddenException if not owned.
    """
    if current_user.role == UserRole.SALES and lead.assigned_to != current_user.id:
        raise ForbiddenException(
            detail="You do not have access to this lead.",
            error_code="LEAD_ACCESS_DENIED",
        )


# ── Service functions ─────────────────────────────────────────────────────────

def list_leads(
    db: Session,
    current_user: User,
    pagination: PaginationParams,
    search: Optional[str] = None,
    stage: Optional[LeadStage] = None,
    assigned_to: Optional[int] = None,
    is_active: Optional[bool] = None,
) -> LeadListResponse:
    """
    Return paginated leads with optional filters.

    For SALES users: always scoped to leads assigned to current_user.id.
    For ADMIN users: all leads visible (no ownership filter).

    Filters:
      search      — case-insensitive match on name, email, phone
      stage       — exact LeadStage filter
      assigned_to — filter by assigned user id (Admin only effective)
      is_active   — True/False; defaults to True (active only) if not provided
    """
    stmt: Select = select(Lead)

    # ── Ownership scoping (critical — done at query level) ────────────────────
    if current_user.role == UserRole.SALES:
        stmt = stmt.where(Lead.assigned_to == current_user.id)

    # ── Active filter: default to active-only unless caller specifies ─────────
    if is_active is None:
        stmt = stmt.where(Lead.is_active.is_(True))
    else:
        stmt = stmt.where(Lead.is_active.is_(is_active))

    # ── Optional filters ──────────────────────────────────────────────────────
    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Lead.name).like(term),
                func.lower(Lead.email).like(term),
                func.lower(Lead.phone).like(term),
            )
        )

    if stage is not None:
        stmt = stmt.where(Lead.stage == stage)

    # Admin can filter by assigned_to; for Sales this would conflict with
    # ownership scope — silently ignored since their scope is already applied.
    if assigned_to is not None and current_user.role == UserRole.ADMIN:
        stmt = stmt.where(Lead.assigned_to == assigned_to)

    # ── Count before pagination ───────────────────────────────────────────────
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Lead.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    leads = db.execute(stmt).scalars().all()

    return LeadListResponse(
        items=[_to_response(l) for l in leads],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


def create_lead(
    db: Session,
    current_user: User,
    data: LeadCreate,
) -> LeadResponse:
    """
    Create a new lead.

    ADMIN: can set assigned_to to any valid active user.
    SALES: assigned_to is always forced to current_user.id regardless of request body.
    """
    if current_user.role == UserRole.SALES:
        # Sales users own their created leads — assignment override not allowed
        effective_assigned_to: Optional[int] = current_user.id
    else:
        # Admin: validate assignee if provided
        effective_assigned_to = data.assigned_to
        if effective_assigned_to is not None:
            _assert_assignee_exists(db, effective_assigned_to)

    lead = Lead(
        name=data.name,
        email=data.email,
        phone=data.phone,
        source=data.source,
        stage=data.stage,
        assigned_to=effective_assigned_to,
        is_active=True,
    )
    db.add(lead)
    db.commit()
    db.refresh(lead)
    logger.info("Lead created: id=%s name=%r by user_id=%s", lead.id, lead.name, current_user.id)
    return _to_response(lead)


def get_lead(
    db: Session,
    current_user: User,
    lead_id: int,
) -> LeadResponse:
    """
    Return a single lead by ID.

    ADMIN: can retrieve any lead.
    SALES: can only retrieve leads assigned to themselves.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)
    return _to_response(lead)


def update_lead(
    db: Session,
    current_user: User,
    lead_id: int,
    data: LeadUpdate,
) -> LeadResponse:
    """
    Partially update a lead.

    ADMIN: can update all fields including assigned_to.
    SALES: can update name/email/phone/source/stage; assigned_to is ignored.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    if data.name is not None:
        lead.name = data.name

    if data.email is not None:
        lead.email = data.email

    if data.phone is not None:
        lead.phone = data.phone

    if data.source is not None:
        lead.source = data.source

    if data.stage is not None:
        lead.stage = data.stage

    # Only Admin can change assignment
    if data.assigned_to is not None and current_user.role == UserRole.ADMIN:
        _assert_assignee_exists(db, data.assigned_to)
        lead.assigned_to = data.assigned_to

    db.commit()
    db.refresh(lead)
    logger.info("Lead updated: id=%s by user_id=%s", lead.id, current_user.id)
    return _to_response(lead)


def delete_lead(
    db: Session,
    current_user: User,
    lead_id: int,
) -> LeadResponse:
    """
    Soft-delete a lead (is_active = False).

    Admin only — enforced at router level via require_admin dependency.
    Historical notes/follow-ups/bookings are NOT deleted.
    """
    lead = _get_lead_or_404(db, lead_id)

    if not lead.is_active:
        # Idempotent: already inactive — return current state
        return _to_response(lead)

    lead.is_active = False
    db.commit()
    db.refresh(lead)
    logger.info("Lead soft-deleted: id=%s by admin user_id=%s", lead.id, current_user.id)
    return _to_response(lead)

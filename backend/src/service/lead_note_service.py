"""
Lead Note service.

Business rules enforced here:
  - Notes are append-only / immutable (no update operation).
  - Creating a note requires the lead to exist and be accessible to the user.
  - ADMIN can add/delete notes on any lead.
  - SALES can add notes only to their assigned leads.
  - SALES can delete only their own notes.
  - ADMIN can delete any note.
  - Viewing notes follows the same ownership rule as viewing a lead.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.models.lead import LeadNoteCreate, LeadNoteListResponse, LeadNoteResponse
from src.repository.models.lead import Lead
from src.repository.models.lead_note import LeadNote
from src.repository.models.user import User
from src.utils.enums import UserRole
from src.utils.exceptions.custom_app_exception import (
    ForbiddenException,
    NotFoundException,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _to_response(note: LeadNote) -> LeadNoteResponse:
    return LeadNoteResponse.model_validate(note)


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


def _get_note_or_404(db: Session, note_id: int) -> LeadNote:
    note: Optional[LeadNote] = db.execute(
        select(LeadNote).where(LeadNote.id == note_id)
    ).scalar_one_or_none()
    if note is None:
        raise NotFoundException(
            detail=f"Note with id {note_id} not found.",
            error_code="LEAD_NOTE_NOT_FOUND",
        )
    return note


# ── Service functions ─────────────────────────────────────────────────────────

def create_note(
    db: Session,
    current_user: User,
    lead_id: int,
    data: LeadNoteCreate,
) -> LeadNoteResponse:
    """
    Append a new note to a lead.

    ADMIN: can add a note to any lead.
    SALES: can add a note only to their assigned lead.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    note = LeadNote(
        lead_id=lead_id,
        user_id=current_user.id,
        note=data.note,
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    logger.info("Lead note created: id=%s lead_id=%s by user_id=%s", note.id, lead_id, current_user.id)
    return _to_response(note)


def list_notes(
    db: Session,
    current_user: User,
    lead_id: int,
) -> LeadNoteListResponse:
    """
    Return all notes for a lead (ordered oldest-first).

    ADMIN: can view notes for any lead.
    SALES: can view notes only for their assigned lead.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    notes = db.execute(
        select(LeadNote)
        .where(LeadNote.lead_id == lead_id)
        .order_by(LeadNote.created_at.asc())
    ).scalars().all()

    return LeadNoteListResponse(
        items=[_to_response(n) for n in notes],
        total=len(notes),
    )


def delete_note(
    db: Session,
    current_user: User,
    lead_id: int,
    note_id: int,
) -> None:
    """
    Delete a note.

    First verifies that the lead exists and is accessible to the user.
    Then:
      ADMIN: can delete any note on that lead.
      SALES: can delete only their own notes (user_id == current_user.id).

    Raises ForbiddenException if a Sales user tries to delete another user's note.
    """
    lead = _get_lead_or_404(db, lead_id)
    _assert_sales_owns_lead(current_user, lead)

    note = _get_note_or_404(db, note_id)

    # Verify the note actually belongs to this lead
    if note.lead_id != lead_id:
        raise NotFoundException(
            detail=f"Note with id {note_id} not found on lead {lead_id}.",
            error_code="LEAD_NOTE_NOT_FOUND",
        )

    # Sales can only delete their own notes
    if current_user.role == UserRole.SALES and note.user_id != current_user.id:
        raise ForbiddenException(
            detail="You can only delete your own notes.",
            error_code="LEAD_NOTE_DELETE_FORBIDDEN",
        )

    db.delete(note)
    db.commit()
    logger.info("Lead note deleted: id=%s lead_id=%s by user_id=%s", note_id, lead_id, current_user.id)

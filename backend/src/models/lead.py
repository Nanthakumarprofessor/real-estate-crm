"""
Pydantic DTOs for Lead, LeadNote, and FollowUp entities.

Distinct from the SQLAlchemy ORM models in repository/models/.
Used exclusively by the router and service layers for request/response shapes.

Models:
  LeadCreate          — POST /api/leads
  LeadUpdate          — PUT  /api/leads/{id}
  LeadResponse        — single lead returned by all endpoints
  LeadListResponse    — paginated list of leads
  LeadNoteCreate      — POST /api/leads/{id}/notes
  LeadNoteResponse    — single note
  LeadNoteListResponse — list of notes for a lead
  FollowUpCreate      — POST /api/leads/{id}/follow-ups
  FollowUpUpdate      — PUT  /api/follow-ups/{id}
  FollowUpResponse    — single follow-up
  FollowUpListResponse — paginated follow-up list
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, EmailStr, field_validator

from src.utils.enums import FollowUpStatus, LeadSource, LeadStage


# ── Lead DTOs ─────────────────────────────────────────────────────────────────

class LeadCreate(BaseModel):
    """Request body for POST /api/leads."""
    name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: Optional[LeadSource] = None
    stage: LeadStage = LeadStage.NEW
    # Only Admin may set/change assigned_to; ignored for Sales on creation
    assigned_to: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def phone_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            if not stripped:
                return None
            return stripped
        return v


class LeadUpdate(BaseModel):
    """
    Request body for PUT /api/leads/{id}.

    All fields optional — only provided fields are updated.
    Sales users cannot change assigned_to; that field is ignored for them
    (enforced in the service layer).
    """
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    source: Optional[LeadSource] = None
    stage: Optional[LeadStage] = None
    assigned_to: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("Name must not be empty.")
        return v.strip() if v else v

    @field_validator("phone")
    @classmethod
    def phone_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v


class AssigneeInfo(BaseModel):
    """Lightweight user reference embedded in lead responses."""
    id: int
    name: str
    email: str

    model_config = {"from_attributes": True}


class LeadResponse(BaseModel):
    """Full lead representation returned by all lead endpoints."""
    id: int
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    source: Optional[LeadSource] = None
    stage: LeadStage
    assigned_to: Optional[int] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    """Paginated response envelope for GET /api/leads."""
    items: List[LeadResponse]
    total: int
    page: int
    size: int


# ── Lead Note DTOs ────────────────────────────────────────────────────────────

class LeadNoteCreate(BaseModel):
    """Request body for POST /api/leads/{lead_id}/notes."""
    note: str

    @field_validator("note")
    @classmethod
    def note_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Note must not be empty.")
        return v.strip()


class LeadNoteResponse(BaseModel):
    """Single note response."""
    id: int
    lead_id: int
    user_id: int
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LeadNoteListResponse(BaseModel):
    """List of notes for a lead (not paginated — notes are bounded per lead)."""
    items: List[LeadNoteResponse]
    total: int


# ── Follow-up DTOs ────────────────────────────────────────────────────────────

class FollowUpCreate(BaseModel):
    """Request body for POST /api/leads/{lead_id}/follow-ups."""
    follow_up_at: datetime
    notes: Optional[str] = None
    status: FollowUpStatus = FollowUpStatus.PENDING

    @field_validator("notes")
    @classmethod
    def notes_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v


class FollowUpUpdate(BaseModel):
    """Request body for PUT /api/follow-ups/{id}."""
    follow_up_at: Optional[datetime] = None
    notes: Optional[str] = None
    status: Optional[FollowUpStatus] = None

    @field_validator("notes")
    @classmethod
    def notes_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v


class FollowUpResponse(BaseModel):
    """Single follow-up response."""
    id: int
    lead_id: int
    assigned_to: int
    follow_up_at: datetime
    notes: Optional[str] = None
    status: FollowUpStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class FollowUpListResponse(BaseModel):
    """Paginated response envelope for follow-up list endpoints."""
    items: List[FollowUpResponse]
    total: int
    page: int
    size: int

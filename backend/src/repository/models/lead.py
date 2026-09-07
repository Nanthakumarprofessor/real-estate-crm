"""
SQLAlchemy ORM model for the `leads` table.

A Lead is a potential property buyer tracked through the sales pipeline.

Key rules:
  - assigned_to is NULLABLE (lead may be unassigned)
  - is_active = soft-delete flag (never physically deleted)
  - stage uses a controlled enum

ON DELETE for assigned_to → users: SET NULL
  (if a user is deleted, their leads remain but become unassigned)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base
from src.utils.enums import LeadSource, LeadStage


class Lead(Base):
    __tablename__ = "leads"

    # ── Table-level indexes ───────────────────────────────────────────────────
    __table_args__ = (
        Index("idx_leads_assigned_to", "assigned_to"),
        Index("idx_leads_stage", "stage"),
        Index("idx_leads_is_active", "is_active"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Fields ────────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)

    source: Mapped[Optional[LeadSource]] = mapped_column(
        Enum(LeadSource, name="lead_source", create_type=True),
        nullable=True,
    )

    stage: Mapped[LeadStage] = mapped_column(
        Enum(LeadStage, name="lead_stage", create_type=True),
        nullable=False,
        default=LeadStage.NEW,
        server_default="NEW",
    )

    # Nullable FK — SET NULL when user is deleted
    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL", name="fk_leads_assigned_to"),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    assignee: Mapped[Optional["User"]] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="assigned_leads",
        foreign_keys=[assigned_to],
    )

    notes: Mapped[list["LeadNote"]] = relationship(  # type: ignore[name-defined]
        "LeadNote",
        back_populates="lead",
        cascade="all, delete-orphan",  # matches ON DELETE CASCADE on lead_notes.lead_id
    )

    follow_ups: Mapped[list["FollowUp"]] = relationship(  # type: ignore[name-defined]
        "FollowUp",
        back_populates="lead",
        cascade="all, delete-orphan",  # matches ON DELETE CASCADE on follow_ups.lead_id
    )

    bookings: Mapped[list["Booking"]] = relationship(  # type: ignore[name-defined]
        "Booking",
        back_populates="lead",
    )

    def __repr__(self) -> str:
        return f"<Lead id={self.id} name={self.name!r} stage={self.stage}>"

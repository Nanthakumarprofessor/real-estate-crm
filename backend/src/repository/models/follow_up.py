"""
SQLAlchemy ORM model for the `follow_ups` table.

Tracks scheduled calls/meetings with lead customers.

ON DELETE rules:
  follow_ups.lead_id     → leads : CASCADE  (delete lead → delete its follow-ups)
  follow_ups.assigned_to → users : RESTRICT (cannot delete user with follow-ups)
"""
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import Optional

from src.repository.database import Base
from src.utils.enums import FollowUpStatus


class FollowUp(Base):
    __tablename__ = "follow_ups"

    # ── Table-level composite index (for dashboard / upcoming queries) ────────
    __table_args__ = (
        Index(
            "idx_followups_assignee_status",
            "assigned_to",
            "status",
            "follow_up_at",
        ),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE", name="fk_follow_ups_lead_id"),
        nullable=False,
        index=True,
    )

    assigned_to: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_follow_ups_assigned_to"),
        nullable=False,
        index=True,
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    follow_up_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[FollowUpStatus] = mapped_column(
        Enum(FollowUpStatus, name="follow_up_status", create_type=True),
        nullable=False,
        default=FollowUpStatus.PENDING,
        server_default="PENDING",
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
    lead: Mapped["Lead"] = relationship(  # type: ignore[name-defined]
        "Lead",
        back_populates="follow_ups",
    )

    assignee: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="follow_ups",
    )

    def __repr__(self) -> str:
        return (
            f"<FollowUp id={self.id} lead_id={self.lead_id} "
            f"status={self.status} follow_up_at={self.follow_up_at}>"
        )

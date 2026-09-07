"""
SQLAlchemy ORM model for the `lead_notes` table.

Notes are IMMUTABLE / APPEND-ONLY for the MVP.
There is intentionally no `updated_at` column because notes cannot be edited.

ON DELETE rules:
  lead_notes.lead_id  → leads : CASCADE  (delete lead → delete its notes)
  lead_notes.user_id  → users : RESTRICT (cannot delete user who has notes)
"""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base


class LeadNote(Base):
    __tablename__ = "lead_notes"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leads.id", ondelete="CASCADE", name="fk_lead_notes_lead_id"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_lead_notes_user_id"),
        nullable=False,
        index=True,
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    note: Mapped[str] = mapped_column(Text, nullable=False)

    # ── Timestamp (created only — no updated_at, notes are immutable) ─────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    lead: Mapped["Lead"] = relationship(  # type: ignore[name-defined]
        "Lead",
        back_populates="notes",
    )

    author: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="notes",
    )

    def __repr__(self) -> str:
        return f"<LeadNote id={self.id} lead_id={self.lead_id} user_id={self.user_id}>"

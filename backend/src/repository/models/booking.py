"""
SQLAlchemy ORM model for the `bookings` table.

A Booking connects a Lead to a Unit, recorded by a User.

Critical rules:
  1. booking_date — server-generated (DEFAULT NOW()). NEVER client-settable.
  2. amount       — nullable; if supplied must be >= 0 (enforced in service layer).
  3. Partial unique index uix_unit_confirmed_booking prevents two CONFIRMED
     bookings for the same unit. This index is created in the Alembic migration
     using op.create_index() with a postgresql_where clause — it cannot be
     expressed purely through __table_args__ in SQLAlchemy ORM.

ON DELETE rules:
  bookings.lead_id   → leads : RESTRICT (cannot delete lead with booking)
  bookings.unit_id   → units : RESTRICT (cannot delete unit with booking)
  bookings.booked_by → users : RESTRICT (cannot delete user who made booking)

Indexes:
  idx_bookings_lead_id   — look up bookings for a lead
  idx_bookings_booked_by — look up bookings made by a user
  idx_bookings_status    — filter by status
  uix_unit_confirmed_booking — partial unique (in migration, not __table_args__)
"""
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base
from src.utils.enums import BookingStatus


class Booking(Base):
    __tablename__ = "bookings"

    # ── Table-level indexes (partial unique index is in Alembic migration) ────
    __table_args__ = (
        Index("idx_bookings_lead_id", "lead_id"),
        Index("idx_bookings_booked_by", "booked_by"),
        Index("idx_bookings_status", "status"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign keys ──────────────────────────────────────────────────────────
    lead_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("leads.id", ondelete="RESTRICT", name="fk_bookings_lead_id"),
        nullable=False,
    )

    unit_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("units.id", ondelete="RESTRICT", name="fk_bookings_unit_id"),
        nullable=False,
    )

    booked_by: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id", ondelete="RESTRICT", name="fk_bookings_booked_by"),
        nullable=False,
    )

    # ── Fields ────────────────────────────────────────────────────────────────

    # Server-generated — always set to NOW() at INSERT time.
    # NOT included in Pydantic request schemas.
    booking_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Optional. If provided, must be >= 0 (validated in service layer).
    amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(14, 2), nullable=True
    )

    status: Mapped[BookingStatus] = mapped_column(
        Enum(BookingStatus, name="booking_status", create_type=True),
        nullable=False,
        default=BookingStatus.CONFIRMED,
        server_default="CONFIRMED",
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
        back_populates="bookings",
    )

    unit: Mapped["Unit"] = relationship(  # type: ignore[name-defined]
        "Unit",
        back_populates="bookings",
    )

    booked_by_user: Mapped["User"] = relationship(  # type: ignore[name-defined]
        "User",
        back_populates="bookings",
        foreign_keys=[booked_by],
    )

    def __repr__(self) -> str:
        return (
            f"<Booking id={self.id} lead_id={self.lead_id} "
            f"unit_id={self.unit_id} status={self.status}>"
        )

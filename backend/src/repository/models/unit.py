"""
SQLAlchemy ORM model for the `units` table.

A Unit is an individual property within a Building (e.g. "A-101").

Critical constraints:
  1. UNIQUE(building_id, unit_number)  — no duplicate unit numbers within a building
  2. ON DELETE RESTRICT on building_id — cannot delete building with units
  3. ON DELETE RESTRICT on bookings    — cannot delete unit with bookings

Indexes:
  idx_units_status              — filter by availability
  idx_units_building_status     — filter available units within a building
"""
from datetime import datetime
from typing import Optional

from decimal import Decimal

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base
from src.utils.enums import UnitStatus, UnitType


class Unit(Base):
    __tablename__ = "units"

    # ── Table-level constraints and indexes ───────────────────────────────────
    __table_args__ = (
        # Critical: no duplicate unit numbers within the same building
        UniqueConstraint(
            "building_id",
            "unit_number",
            name="uix_building_unit_number",
        ),
        Index("idx_units_status", "status"),
        Index("idx_units_building_status", "building_id", "status"),
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    building_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "buildings.id", ondelete="RESTRICT", name="fk_units_building_id"
        ),
        nullable=False,
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    unit_number: Mapped[str] = mapped_column(String(50), nullable=False)

    type: Mapped[UnitType] = mapped_column(
        # values_callable ensures PostgreSQL stores the enum *values* (1BHK, 2BHK...)
        # not the Python attribute names (ONE_BHK, TWO_BHK...)
        Enum(UnitType, name="unit_type", create_type=True, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    floor: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Numeric(12, 2) supports values up to 9,999,999,999.99
    # Nullable — price may not be set at creation time
    price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    status: Mapped[UnitStatus] = mapped_column(
        Enum(UnitStatus, name="unit_status", create_type=True),
        nullable=False,
        default=UnitStatus.AVAILABLE,
        server_default="AVAILABLE",
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
    building: Mapped["Building"] = relationship(  # type: ignore[name-defined]
        "Building",
        back_populates="units",
    )

    bookings: Mapped[list["Booking"]] = relationship(  # type: ignore[name-defined]
        "Booking",
        back_populates="unit",
    )

    def __repr__(self) -> str:
        return (
            f"<Unit id={self.id} unit_number={self.unit_number!r} "
            f"building_id={self.building_id} status={self.status}>"
        )

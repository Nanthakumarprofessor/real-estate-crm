"""
SQLAlchemy ORM model for the `buildings` table.

A Building belongs to a Project and contains Units (e.g. "Tower A").

ON DELETE rules:
  buildings.project_id → projects : RESTRICT (cannot delete project with buildings)
  units.building_id    → buildings: RESTRICT (cannot delete building with units)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base


class Building(Base):
    __tablename__ = "buildings"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Foreign key ───────────────────────────────────────────────────────────
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("projects.id", ondelete="RESTRICT", name="fk_buildings_project_id"),
        nullable=False,
        index=True,
    )

    # ── Fields ────────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    total_floors: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

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
    project: Mapped["Project"] = relationship(  # type: ignore[name-defined]
        "Project",
        back_populates="buildings",
    )

    units: Mapped[list["Unit"]] = relationship(  # type: ignore[name-defined]
        "Unit",
        back_populates="building",
    )

    def __repr__(self) -> str:
        return f"<Building id={self.id} name={self.name!r} project_id={self.project_id}>"

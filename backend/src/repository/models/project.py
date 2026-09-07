"""
SQLAlchemy ORM model for the `projects` table.

A Project is the top-level property hierarchy entity (e.g. "ABC Residency").

ON DELETE rule:
  buildings.project_id → projects : RESTRICT
  (cannot delete a project that has associated buildings)
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base


class Project(Base):
    __tablename__ = "projects"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Fields ────────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)

    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

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
    buildings: Mapped[list["Building"]] = relationship(  # type: ignore[name-defined]
        "Building",
        back_populates="project",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"

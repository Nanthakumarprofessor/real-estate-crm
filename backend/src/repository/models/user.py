"""
SQLAlchemy ORM model for the `users` table.

Stores CRM users (Admin and Sales employees).
Passwords are NEVER stored as plaintext — only bcrypt hashes.

ON DELETE rules for relationships originating from users:
  users → leads       (assigned_to)  : SET NULL
  users → lead_notes  (user_id)      : RESTRICT
  users → follow_ups  (assigned_to)  : RESTRICT
  users → bookings    (booked_by)    : RESTRICT
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.repository.database import Base
from src.utils.enums import UserRole


class User(Base):
    __tablename__ = "users"

    # ── Primary key ───────────────────────────────────────────────────────────
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ── Fields ────────────────────────────────────────────────────────────────
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,   # enforced by DB UNIQUE constraint
        index=True,    # fast login lookups
    )

    # Stores only bcrypt hash — never plaintext
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_type=True),
        nullable=False,
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

    # updated_at auto-updates on every row change via onupdate
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    # ── Relationships (back-references populated by child models) ─────────────
    # leads assigned to this user (FK: leads.assigned_to)
    assigned_leads: Mapped[list["Lead"]] = relationship(  # type: ignore[name-defined]
        "Lead",
        back_populates="assignee",
        foreign_keys="Lead.assigned_to",
    )

    # notes authored by this user
    notes: Mapped[list["LeadNote"]] = relationship(  # type: ignore[name-defined]
        "LeadNote",
        back_populates="author",
    )

    # follow-ups assigned to this user
    follow_ups: Mapped[list["FollowUp"]] = relationship(  # type: ignore[name-defined]
        "FollowUp",
        back_populates="assignee",
    )

    # bookings created by this user
    bookings: Mapped[list["Booking"]] = relationship(  # type: ignore[name-defined]
        "Booking",
        back_populates="booked_by_user",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email!r} role={self.role}>"

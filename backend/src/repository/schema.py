"""
Central ORM model registry.

All SQLAlchemy models are imported here so that:
  1. Alembic's env.py discovers every table via Base.metadata.
  2. Application code can import models from one place.
  3. Relationships resolve correctly (all models loaded before SQLAlchemy
     resolves string-based forward references).

Import order follows FK dependency:
  users → leads, lead_notes, follow_ups, bookings
  projects → buildings → units → bookings
"""

# Re-export Base (alembic/env.py imports Base from here)
from src.repository.database import Base  # noqa: F401

# ── Import every ORM model so Alembic autogenerate detects them ───────────────
from src.repository.models.user import User  # noqa: F401
from src.repository.models.lead import Lead  # noqa: F401
from src.repository.models.lead_note import LeadNote  # noqa: F401
from src.repository.models.follow_up import FollowUp  # noqa: F401
from src.repository.models.project import Project  # noqa: F401
from src.repository.models.building import Building  # noqa: F401
from src.repository.models.unit import Unit  # noqa: F401
from src.repository.models.booking import Booking  # noqa: F401

__all__ = [
    "Base",
    "User",
    "Lead",
    "LeadNote",
    "FollowUp",
    "Project",
    "Building",
    "Unit",
    "Booking",
]

"""
All application enums as defined in the SD v2.

These enums are shared between:
  - SQLAlchemy ORM models (repository/schema.py)  — Phase 2
  - Pydantic request/response models (src/models/) — Phase 2+
  - Service layer business logic

Keeping them in one place prevents duplication and drift.
"""
import enum


class UserRole(str, enum.Enum):
    """User roles for RBAC."""
    ADMIN = "ADMIN"
    SALES = "SALES"


class LeadStage(str, enum.Enum):
    """Sales pipeline stages for a lead."""
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    SITE_VISIT = "SITE_VISIT"
    INTERESTED = "INTERESTED"
    NEGOTIATION = "NEGOTIATION"
    BOOKED = "BOOKED"
    LOST = "LOST"


class LeadSource(str, enum.Enum):
    """Channel through which a lead was acquired."""
    WEBSITE = "WEBSITE"
    REFERRAL = "REFERRAL"
    ADVERTISEMENT = "ADVERTISEMENT"
    WALK_IN = "WALK_IN"
    SOCIAL_MEDIA = "SOCIAL_MEDIA"
    OTHER = "OTHER"


class UnitType(str, enum.Enum):
    """Property unit configurations.
    
    The enum *values* (1BHK, 2BHK ...) are what gets stored in PostgreSQL.
    Python identifiers cannot start with a digit, so we use descriptive names
    but the string value matches the SD exactly.
    """
    ONE_BHK = "1BHK"
    TWO_BHK = "2BHK"
    THREE_BHK = "3BHK"
    FOUR_BHK = "4BHK"
    VILLA = "VILLA"
    PLOT = "PLOT"


class UnitStatus(str, enum.Enum):
    """Availability status of a property unit."""
    AVAILABLE = "AVAILABLE"
    BOOKED = "BOOKED"


class BookingStatus(str, enum.Enum):
    """Lifecycle status of a booking record."""
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"


class FollowUpStatus(str, enum.Enum):
    """Status of a scheduled customer follow-up."""
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

"""
Application-level error codes.

Each constant is a short machine-readable string that identifies the
error category. These are included in error responses alongside the
human-readable `detail` message.

Convention: DOMAIN_REASON  (uppercase, underscores)
"""

# ── Authentication / Authorisation ────────────────────────────────────────────
AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"
AUTH_TOKEN_EXPIRED = "AUTH_TOKEN_EXPIRED"
AUTH_TOKEN_INVALID = "AUTH_TOKEN_INVALID"
AUTH_ACCOUNT_INACTIVE = "AUTH_ACCOUNT_INACTIVE"

# ── Authorisation ─────────────────────────────────────────────────────────────
PERMISSION_DENIED = "PERMISSION_DENIED"

# ── Generic resource errors ───────────────────────────────────────────────────
RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
RESOURCE_ALREADY_EXISTS = "RESOURCE_ALREADY_EXISTS"
VALIDATION_ERROR = "VALIDATION_ERROR"

# ── Lead ──────────────────────────────────────────────────────────────────────
LEAD_NOT_FOUND = "LEAD_NOT_FOUND"
LEAD_INACTIVE = "LEAD_INACTIVE"
LEAD_ACCESS_DENIED = "LEAD_ACCESS_DENIED"

# ── Unit ──────────────────────────────────────────────────────────────────────
UNIT_NOT_FOUND = "UNIT_NOT_FOUND"
UNIT_NOT_AVAILABLE = "UNIT_NOT_AVAILABLE"

# ── Booking ───────────────────────────────────────────────────────────────────
BOOKING_NOT_FOUND = "BOOKING_NOT_FOUND"
BOOKING_ALREADY_EXISTS = "BOOKING_ALREADY_EXISTS"
BOOKING_UNIT_ALREADY_BOOKED = "BOOKING_UNIT_ALREADY_BOOKED"
BOOKING_NOT_CONFIRMED = "BOOKING_NOT_CONFIRMED"
BOOKING_CANCEL_DENIED = "BOOKING_CANCEL_DENIED"

# ── User ──────────────────────────────────────────────────────────────────────
USER_NOT_FOUND = "USER_NOT_FOUND"
USER_EMAIL_TAKEN = "USER_EMAIL_TAKEN"
USER_INACTIVE = "USER_INACTIVE"

# ── Property ──────────────────────────────────────────────────────────────────
PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
BUILDING_NOT_FOUND = "BUILDING_NOT_FOUND"
PROJECT_HAS_BUILDINGS = "PROJECT_HAS_BUILDINGS"
BUILDING_HAS_UNITS = "BUILDING_HAS_UNITS"
UNIT_HAS_BOOKING = "UNIT_HAS_BOOKING"

# ── Follow-up ─────────────────────────────────────────────────────────────────
FOLLOWUP_NOT_FOUND = "FOLLOWUP_NOT_FOUND"
FOLLOWUP_DATE_IN_PAST = "FOLLOWUP_DATE_IN_PAST"

# ── Note ──────────────────────────────────────────────────────────────────────
NOTE_NOT_FOUND = "NOTE_NOT_FOUND"
NOTE_DELETE_DENIED = "NOTE_DELETE_DENIED"

# ── Internal ──────────────────────────────────────────────────────────────────
INTERNAL_SERVER_ERROR = "INTERNAL_SERVER_ERROR"
DATABASE_ERROR = "DATABASE_ERROR"

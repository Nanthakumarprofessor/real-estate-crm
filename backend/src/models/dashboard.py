"""
Pydantic DTOs for the Dashboard summary endpoint.

All values are computed from aggregate database queries.
No database-internal fields are exposed.

DashboardSummaryResponse
  ├── LeadStatistics
  │     total        — total active leads visible to the user
  │     by_stage     — dict[LeadStage, int], ALL stages always present (zeros included)
  ├── FollowUpStatistics
  │     upcoming     — PENDING, follow_up_at >= now
  │     overdue      — PENDING, follow_up_at < now
  ├── PropertyStatistics
  │     total_units
  │     available_units
  │     booked_units
  └── BookingStatistics
        confirmed
        cancelled
"""
from typing import Dict

from pydantic import BaseModel

from src.utils.enums import LeadStage


class LeadStatistics(BaseModel):
    total: int
    by_stage: Dict[str, int]  # keyed by LeadStage.value, all stages always present


class FollowUpStatistics(BaseModel):
    upcoming: int   # PENDING and follow_up_at >= NOW()
    overdue: int    # PENDING and follow_up_at <  NOW()


class PropertyStatistics(BaseModel):
    total_units: int
    available_units: int
    booked_units: int


class BookingStatistics(BaseModel):
    confirmed: int
    cancelled: int


class DashboardSummaryResponse(BaseModel):
    leads: LeadStatistics
    follow_ups: FollowUpStatistics
    properties: PropertyStatistics
    bookings: BookingStatistics

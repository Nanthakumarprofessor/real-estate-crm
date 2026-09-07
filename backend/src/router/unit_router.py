"""
Unit management router.

Endpoints (nested under buildings):
  POST   /api/buildings/{building_id}/units   — create unit (Admin only)
  GET    /api/buildings/{building_id}/units   — list units (authenticated)

Endpoints (direct unit access):
  GET    /api/units/{id}   — get unit (authenticated)
  PUT    /api/units/{id}   — update unit (Admin only)
  DELETE /api/units/{id}   — delete unit (Admin only)

Authorization:
  Mutations → require_admin
  Reads     → get_current_user (both ADMIN and SALES)

Sales need read access to units to check availability before booking (Phase 7).
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import get_current_user, require_admin
from src.models.api_response_dto import SuccessResponse
from src.models.property import (
    UnitCreate,
    UnitListResponse,
    UnitResponse,
    UnitUpdate,
)
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import property_service
from src.utils.enums import UnitStatus, UnitType
from src.utils.pagination import PaginationParams

# ── Router mounted at /api/buildings/{building_id}/units ──────────────────────
nested_router = APIRouter()


@nested_router.post(
    "",
    response_model=UnitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a unit in a building (Admin only)",
)
def create_unit(
    building_id: int,
    data: UnitCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UnitResponse:
    """
    POST /api/buildings/{building_id}/units — Admin only.

    Returns 409 on duplicate unit_number within the same building.
    """
    return property_service.create_unit(db=db, building_id=building_id, data=data)


@nested_router.get(
    "",
    response_model=UnitListResponse,
    status_code=status.HTTP_200_OK,
    summary="List units in a building",
)
def list_units(
    building_id: int,
    status: Optional[UnitStatus] = Query(
        default=None,
        description="Filter by unit status (AVAILABLE / BOOKED)",
    ),
    type: Optional[UnitType] = Query(
        default=None,
        description="Filter by unit type (1BHK, 2BHK, etc.)",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> UnitListResponse:
    """GET /api/buildings/{building_id}/units — Admin and Sales."""
    return property_service.list_units(
        db=db,
        building_id=building_id,
        pagination=pagination,
        status=status,
        unit_type=type,
    )


# ── Router mounted at /api/units ──────────────────────────────────────────────
router = APIRouter()


@router.get(
    "/{unit_id}",
    response_model=UnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a unit by ID",
)
def get_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> UnitResponse:
    """GET /api/units/{id} — Admin and Sales."""
    return property_service.get_unit(db=db, unit_id=unit_id)


@router.put(
    "/{unit_id}",
    response_model=UnitResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a unit (Admin only)",
)
def update_unit(
    unit_id: int,
    data: UnitUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> UnitResponse:
    """PUT /api/units/{id} — Admin only."""
    return property_service.update_unit(db=db, unit_id=unit_id, data=data)


@router.delete(
    "/{unit_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a unit (Admin only)",
)
def delete_unit(
    unit_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SuccessResponse:
    """
    DELETE /api/units/{id} — Admin only.

    Returns 409 if the unit has associated booking records.
    """
    property_service.delete_unit(db=db, unit_id=unit_id)
    return SuccessResponse(message="Unit deleted successfully.")

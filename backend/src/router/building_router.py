"""
Building management router.

Endpoints (nested under projects):
  POST   /api/projects/{project_id}/buildings   — create building (Admin only)
  GET    /api/projects/{project_id}/buildings   — list buildings (authenticated)

Endpoints (direct building access):
  GET    /api/buildings/{id}   — get building (authenticated)
  PUT    /api/buildings/{id}   — update building (Admin only)
  DELETE /api/buildings/{id}   — delete building (Admin only)

Authorization:
  Mutations → require_admin
  Reads     → get_current_user (both ADMIN and SALES)

Note:
  The nested POST/GET routes live on the projects router prefix (/api/projects).
  The flat GET/PUT/DELETE routes live on the buildings prefix (/api/buildings).
  Both routers are registered in router.py.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.core.security import get_current_user, require_admin
from src.models.api_response_dto import SuccessResponse
from src.models.property import (
    BuildingCreate,
    BuildingListResponse,
    BuildingResponse,
    BuildingUpdate,
)
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import property_service

# ── Router mounted at /api/projects/{project_id}/buildings ────────────────────
nested_router = APIRouter()


@nested_router.post(
    "",
    response_model=BuildingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a building under a project (Admin only)",
)
def create_building(
    project_id: int,
    data: BuildingCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BuildingResponse:
    """POST /api/projects/{project_id}/buildings — Admin only."""
    return property_service.create_building(db=db, project_id=project_id, data=data)


@nested_router.get(
    "",
    response_model=BuildingListResponse,
    status_code=status.HTTP_200_OK,
    summary="List buildings for a project",
)
def list_buildings(
    project_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> BuildingListResponse:
    """GET /api/projects/{project_id}/buildings — Admin and Sales."""
    return property_service.list_buildings(db=db, project_id=project_id)


# ── Router mounted at /api/buildings ─────────────────────────────────────────
router = APIRouter()


@router.get(
    "/{building_id}",
    response_model=BuildingResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a building by ID",
)
def get_building(
    building_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> BuildingResponse:
    """GET /api/buildings/{id} — Admin and Sales."""
    return property_service.get_building(db=db, building_id=building_id)


@router.put(
    "/{building_id}",
    response_model=BuildingResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a building (Admin only)",
)
def update_building(
    building_id: int,
    data: BuildingUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> BuildingResponse:
    """PUT /api/buildings/{id} — Admin only."""
    return property_service.update_building(db=db, building_id=building_id, data=data)


@router.delete(
    "/{building_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a building (Admin only)",
)
def delete_building(
    building_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SuccessResponse:
    """
    DELETE /api/buildings/{id} — Admin only.

    Returns 409 if the building has associated units.
    """
    property_service.delete_building(db=db, building_id=building_id)
    return SuccessResponse(message="Building deleted successfully.")

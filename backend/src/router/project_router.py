"""
Project management router.

Endpoints:
  POST   /api/projects          — create a project (Admin only)
  GET    /api/projects          — list projects (authenticated)
  GET    /api/projects/{id}     — get project (authenticated)
  PUT    /api/projects/{id}     — update project (Admin only)
  DELETE /api/projects/{id}     — delete project (Admin only)

Authorization:
  Mutations → require_admin
  Reads     → get_current_user (both ADMIN and SALES)
"""
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.core.security import get_current_user, require_admin
from src.models.api_response_dto import SuccessResponse
from src.models.property import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from src.repository.database import get_db
from src.repository.models.user import User
from src.service import property_service
from src.utils.pagination import PaginationParams

router = APIRouter()


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project (Admin only)",
)
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ProjectResponse:
    """POST /api/projects — Admin only."""
    return property_service.create_project(db=db, data=data)


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List projects",
)
def list_projects(
    search: Optional[str] = Query(
        default=None,
        description="Search by project name or location (case-insensitive substring)",
    ),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ProjectListResponse:
    """GET /api/projects — Admin and Sales."""
    return property_service.list_projects(db=db, pagination=pagination, search=search)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a project by ID",
)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
) -> ProjectResponse:
    """GET /api/projects/{id} — Admin and Sales."""
    return property_service.get_project(db=db, project_id=project_id)


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a project (Admin only)",
)
def update_project(
    project_id: int,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> ProjectResponse:
    """PUT /api/projects/{id} — Admin only."""
    return property_service.update_project(db=db, project_id=project_id, data=data)


@router.delete(
    "/{project_id}",
    response_model=SuccessResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete a project (Admin only)",
)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SuccessResponse:
    """
    DELETE /api/projects/{id} — Admin only.

    Returns 409 if the project has associated buildings.
    """
    property_service.delete_project(db=db, project_id=project_id)
    return SuccessResponse(message="Project deleted successfully.")

"""
Pydantic DTOs for Project, Building, and Unit entities.

Distinct from the SQLAlchemy ORM models in repository/models/.
Used exclusively by the router and service layers.

Models:
  ProjectCreate       — POST /api/projects
  ProjectUpdate       — PUT  /api/projects/{id}
  ProjectResponse     — single project response

  BuildingCreate      — POST /api/projects/{id}/buildings
  BuildingUpdate      — PUT  /api/buildings/{id}
  BuildingResponse    — single building response

  UnitCreate          — POST /api/buildings/{id}/units
  UnitUpdate          — PUT  /api/units/{id}
  UnitResponse        — single unit response

  ProjectListResponse  — paginated project list
  BuildingListResponse — list of buildings for a project
  UnitListResponse     — paginated unit list
"""
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, field_validator

from src.utils.enums import UnitStatus, UnitType


# ── Project DTOs ──────────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    """Request body for POST /api/projects."""
    name: str
    location: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Project name must not be empty.")
        return v.strip()

    @field_validator("location")
    @classmethod
    def location_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v

    @field_validator("description")
    @classmethod
    def description_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            stripped = v.strip()
            return stripped if stripped else None
        return v


class ProjectUpdate(BaseModel):
    """Request body for PUT /api/projects/{id}. All fields optional."""
    name: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Project name must not be empty.")
            return v.strip()
        return v

    @field_validator("location")
    @classmethod
    def location_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v

    @field_validator("description")
    @classmethod
    def description_stripped(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return v.strip() or None
        return v


class ProjectResponse(BaseModel):
    """Full project representation."""
    id: int
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProjectListResponse(BaseModel):
    """Paginated response envelope for GET /api/projects."""
    items: List[ProjectResponse]
    total: int
    page: int
    size: int


# ── Building DTOs ─────────────────────────────────────────────────────────────

class BuildingCreate(BaseModel):
    """Request body for POST /api/projects/{project_id}/buildings."""
    name: str
    total_floors: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Building name must not be empty.")
        return v.strip()

    @field_validator("total_floors")
    @classmethod
    def total_floors_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("total_floors must be at least 1.")
        return v


class BuildingUpdate(BaseModel):
    """Request body for PUT /api/buildings/{id}. All fields optional."""
    name: Optional[str] = None
    total_floors: Optional[int] = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("Building name must not be empty.")
            return v.strip()
        return v

    @field_validator("total_floors")
    @classmethod
    def total_floors_positive(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("total_floors must be at least 1.")
        return v


class BuildingResponse(BaseModel):
    """Full building representation."""
    id: int
    project_id: int
    name: str
    total_floors: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BuildingListResponse(BaseModel):
    """List of buildings for a project (not paginated — bounded per project)."""
    items: List[BuildingResponse]
    total: int


# ── Unit DTOs ─────────────────────────────────────────────────────────────────

class UnitCreate(BaseModel):
    """Request body for POST /api/buildings/{building_id}/units."""
    unit_number: str
    type: UnitType
    floor: Optional[int] = None
    price: Optional[Decimal] = None
    status: UnitStatus = UnitStatus.AVAILABLE

    @field_validator("unit_number")
    @classmethod
    def unit_number_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("unit_number must not be empty.")
        return v.strip()

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("price must be non-negative.")
        return v

    @field_validator("floor")
    @classmethod
    def floor_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("floor must be 0 or greater.")
        return v


class UnitUpdate(BaseModel):
    """Request body for PUT /api/units/{id}. All fields optional."""
    unit_number: Optional[str] = None
    type: Optional[UnitType] = None
    floor: Optional[int] = None
    price: Optional[Decimal] = None
    status: Optional[UnitStatus] = None

    @field_validator("unit_number")
    @classmethod
    def unit_number_not_empty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not v.strip():
                raise ValueError("unit_number must not be empty.")
            return v.strip()
        return v

    @field_validator("price")
    @classmethod
    def price_non_negative(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        if v is not None and v < 0:
            raise ValueError("price must be non-negative.")
        return v

    @field_validator("floor")
    @classmethod
    def floor_non_negative(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 0:
            raise ValueError("floor must be 0 or greater.")
        return v


class UnitResponse(BaseModel):
    """Full unit representation."""
    id: int
    building_id: int
    unit_number: str
    type: UnitType
    floor: Optional[int] = None
    price: Optional[Decimal] = None
    status: UnitStatus
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UnitListResponse(BaseModel):
    """Paginated response envelope for GET /api/buildings/{id}/units."""
    items: List[UnitResponse]
    total: int
    page: int
    size: int

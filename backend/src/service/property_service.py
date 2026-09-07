"""
Property management service.

Covers Projects, Buildings, and Units.

Authorization is enforced at the router layer (require_admin / get_current_user).
This service layer handles business logic, conflict detection, and query composition.

Delete dependency rules:
  Project  → cannot delete if it has Buildings  (RESTRICT FK in DB)
  Building → cannot delete if it has Units       (RESTRICT FK in DB)
  Unit     → cannot delete if it has Bookings    (RESTRICT FK in DB)

We check at the application level before hitting the DB constraint so the
client receives a meaningful 409 rather than a raw IntegrityError.

IntegrityError is also caught as a last-resort safety net.
"""
from typing import Optional

from sqlalchemy import Select, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models.property import (
    BuildingCreate,
    BuildingListResponse,
    BuildingResponse,
    BuildingUpdate,
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    UnitCreate,
    UnitListResponse,
    UnitResponse,
    UnitUpdate,
)
from src.repository.models.booking import Booking
from src.repository.models.building import Building
from src.repository.models.project import Project
from src.repository.models.unit import Unit
from src.utils.enums import UnitStatus, UnitType
from src.utils.exceptions.custom_app_exception import (
    ConflictException,
    NotFoundException,
)
from src.utils.logger import get_logger
from src.utils.pagination import PaginationParams

logger = get_logger(__name__)


# ── Converters ────────────────────────────────────────────────────────────────

def _project_response(p: Project) -> ProjectResponse:
    return ProjectResponse.model_validate(p)


def _building_response(b: Building) -> BuildingResponse:
    return BuildingResponse.model_validate(b)


def _unit_response(u: Unit) -> UnitResponse:
    return UnitResponse.model_validate(u)


# ── Shared lookups ────────────────────────────────────────────────────────────

def _get_project_or_404(db: Session, project_id: int) -> Project:
    project: Optional[Project] = db.execute(
        select(Project).where(Project.id == project_id)
    ).scalar_one_or_none()
    if project is None:
        raise NotFoundException(
            detail=f"Project with id {project_id} not found.",
            error_code="PROJECT_NOT_FOUND",
        )
    return project


def _get_building_or_404(db: Session, building_id: int) -> Building:
    building: Optional[Building] = db.execute(
        select(Building).where(Building.id == building_id)
    ).scalar_one_or_none()
    if building is None:
        raise NotFoundException(
            detail=f"Building with id {building_id} not found.",
            error_code="BUILDING_NOT_FOUND",
        )
    return building


def _get_unit_or_404(db: Session, unit_id: int) -> Unit:
    unit: Optional[Unit] = db.execute(
        select(Unit).where(Unit.id == unit_id)
    ).scalar_one_or_none()
    if unit is None:
        raise NotFoundException(
            detail=f"Unit with id {unit_id} not found.",
            error_code="UNIT_NOT_FOUND",
        )
    return unit


# ═════════════════════════════════════════════════════════════════════════════
# PROJECT SERVICE
# ═════════════════════════════════════════════════════════════════════════════

def create_project(db: Session, data: ProjectCreate) -> ProjectResponse:
    """Create a new project."""
    project = Project(
        name=data.name,
        location=data.location,
        description=data.description,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    logger.info("Project created: id=%s name=%r", project.id, project.name)
    return _project_response(project)


def list_projects(
    db: Session,
    pagination: PaginationParams,
    search: Optional[str] = None,
) -> ProjectListResponse:
    """
    Return paginated projects.

    Optional search: case-insensitive substring on name or location.
    """
    stmt: Select = select(Project)

    if search:
        term = f"%{search.strip().lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Project.name).like(term),
                func.lower(Project.location).like(term),
            )
        )

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Project.created_at.desc()).offset(pagination.offset).limit(pagination.limit)
    projects = db.execute(stmt).scalars().all()

    return ProjectListResponse(
        items=[_project_response(p) for p in projects],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


def get_project(db: Session, project_id: int) -> ProjectResponse:
    return _project_response(_get_project_or_404(db, project_id))


def update_project(db: Session, project_id: int, data: ProjectUpdate) -> ProjectResponse:
    """Partially update a project."""
    project = _get_project_or_404(db, project_id)

    if data.name is not None:
        project.name = data.name
    if data.location is not None:
        project.location = data.location
    if data.description is not None:
        project.description = data.description

    db.commit()
    db.refresh(project)
    logger.info("Project updated: id=%s", project.id)
    return _project_response(project)


def delete_project(db: Session, project_id: int) -> None:
    """
    Delete a project.

    Raises ConflictException if the project has associated buildings.
    The DB FK is RESTRICT so we check application-side first for a clean error.
    """
    project = _get_project_or_404(db, project_id)

    building_count: int = db.execute(
        select(func.count()).where(Building.project_id == project_id)
    ).scalar_one()

    if building_count > 0:
        raise ConflictException(
            detail="Cannot delete project because it contains buildings.",
            error_code="PROJECT_HAS_BUILDINGS",
        )

    try:
        db.delete(project)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail="Cannot delete project because it contains buildings.",
            error_code="PROJECT_HAS_BUILDINGS",
        )
    logger.info("Project deleted: id=%s", project_id)


# ═════════════════════════════════════════════════════════════════════════════
# BUILDING SERVICE
# ═════════════════════════════════════════════════════════════════════════════

def create_building(
    db: Session, project_id: int, data: BuildingCreate
) -> BuildingResponse:
    """Create a building under an existing project."""
    _get_project_or_404(db, project_id)  # 404 if project doesn't exist

    building = Building(
        project_id=project_id,
        name=data.name,
        total_floors=data.total_floors,
    )
    db.add(building)
    db.commit()
    db.refresh(building)
    logger.info("Building created: id=%s project_id=%s name=%r", building.id, project_id, building.name)
    return _building_response(building)


def list_buildings(db: Session, project_id: int) -> BuildingListResponse:
    """
    Return all buildings for a project.

    Verifies the project exists first (404 if not).
    """
    _get_project_or_404(db, project_id)

    buildings = db.execute(
        select(Building)
        .where(Building.project_id == project_id)
        .order_by(Building.created_at.asc())
    ).scalars().all()

    return BuildingListResponse(
        items=[_building_response(b) for b in buildings],
        total=len(buildings),
    )


def get_building(db: Session, building_id: int) -> BuildingResponse:
    return _building_response(_get_building_or_404(db, building_id))


def update_building(
    db: Session, building_id: int, data: BuildingUpdate
) -> BuildingResponse:
    """Partially update a building. project_id cannot be changed."""
    building = _get_building_or_404(db, building_id)

    if data.name is not None:
        building.name = data.name
    if data.total_floors is not None:
        building.total_floors = data.total_floors

    db.commit()
    db.refresh(building)
    logger.info("Building updated: id=%s", building.id)
    return _building_response(building)


def delete_building(db: Session, building_id: int) -> None:
    """
    Delete a building.

    Raises ConflictException if the building contains units.
    """
    building = _get_building_or_404(db, building_id)

    unit_count: int = db.execute(
        select(func.count()).where(Unit.building_id == building_id)
    ).scalar_one()

    if unit_count > 0:
        raise ConflictException(
            detail="Cannot delete building because it contains units.",
            error_code="BUILDING_HAS_UNITS",
        )

    try:
        db.delete(building)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail="Cannot delete building because it contains units.",
            error_code="BUILDING_HAS_UNITS",
        )
    logger.info("Building deleted: id=%s", building_id)


# ═════════════════════════════════════════════════════════════════════════════
# UNIT SERVICE
# ═════════════════════════════════════════════════════════════════════════════

def create_unit(
    db: Session, building_id: int, data: UnitCreate
) -> UnitResponse:
    """
    Create a unit under an existing building.

    Checks for duplicate unit_number within the same building before inserting.
    Also catches IntegrityError as a concurrency safety net.
    """
    _get_building_or_404(db, building_id)  # 404 if building doesn't exist

    # Application-level uniqueness check for a clean 409
    existing: Optional[Unit] = db.execute(
        select(Unit).where(
            Unit.building_id == building_id,
            Unit.unit_number == data.unit_number,
        )
    ).scalar_one_or_none()
    if existing:
        raise ConflictException(
            detail=f"Unit number '{data.unit_number}' already exists in this building.",
            error_code="UNIT_NUMBER_DUPLICATE",
        )

    unit = Unit(
        building_id=building_id,
        unit_number=data.unit_number,
        type=data.type,
        floor=data.floor,
        price=data.price,
        status=data.status,
    )
    db.add(unit)

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail=f"Unit number '{data.unit_number}' already exists in this building.",
            error_code="UNIT_NUMBER_DUPLICATE",
        )

    db.commit()
    db.refresh(unit)
    logger.info("Unit created: id=%s building_id=%s number=%r", unit.id, building_id, unit.unit_number)
    return _unit_response(unit)


def list_units(
    db: Session,
    building_id: int,
    pagination: PaginationParams,
    status: Optional[UnitStatus] = None,
    unit_type: Optional[UnitType] = None,
) -> UnitListResponse:
    """
    Return paginated units for a building.

    Verifies the building exists first (404 if not).
    Supports optional status and type filters at the DB level.
    """
    _get_building_or_404(db, building_id)

    stmt: Select = select(Unit).where(Unit.building_id == building_id)

    if status is not None:
        stmt = stmt.where(Unit.status == status)
    if unit_type is not None:
        stmt = stmt.where(Unit.type == unit_type)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total: int = db.execute(count_stmt).scalar_one()

    stmt = stmt.order_by(Unit.unit_number.asc()).offset(pagination.offset).limit(pagination.limit)
    units = db.execute(stmt).scalars().all()

    return UnitListResponse(
        items=[_unit_response(u) for u in units],
        total=total,
        page=pagination.page,
        size=pagination.size,
    )


def get_unit(db: Session, unit_id: int) -> UnitResponse:
    return _unit_response(_get_unit_or_404(db, unit_id))


def update_unit(db: Session, unit_id: int, data: UnitUpdate) -> UnitResponse:
    """
    Partially update a unit.

    building_id cannot be changed.
    If unit_number changes, checks for duplicate within the same building.
    """
    unit = _get_unit_or_404(db, unit_id)

    # Duplicate unit_number check if number is being changed
    if data.unit_number is not None and data.unit_number != unit.unit_number:
        conflict: Optional[Unit] = db.execute(
            select(Unit).where(
                Unit.building_id == unit.building_id,
                Unit.unit_number == data.unit_number,
                Unit.id != unit_id,
            )
        ).scalar_one_or_none()
        if conflict:
            raise ConflictException(
                detail=f"Unit number '{data.unit_number}' already exists in this building.",
                error_code="UNIT_NUMBER_DUPLICATE",
            )
        unit.unit_number = data.unit_number

    if data.type is not None:
        unit.type = data.type
    if data.floor is not None:
        unit.floor = data.floor
    if data.price is not None:
        unit.price = data.price
    if data.status is not None:
        unit.status = data.status

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail=f"Unit number '{data.unit_number}' already exists in this building.",
            error_code="UNIT_NUMBER_DUPLICATE",
        )

    db.commit()
    db.refresh(unit)
    logger.info("Unit updated: id=%s", unit.id)
    return _unit_response(unit)


def delete_unit(db: Session, unit_id: int) -> None:
    """
    Delete a unit.

    Raises ConflictException if any booking records reference this unit.
    The DB FK is RESTRICT — we check at the app level for a clean error.
    """
    unit = _get_unit_or_404(db, unit_id)

    booking_count: int = db.execute(
        select(func.count()).where(Booking.unit_id == unit_id)
    ).scalar_one()

    if booking_count > 0:
        raise ConflictException(
            detail="Cannot delete unit because booking history exists.",
            error_code="UNIT_HAS_BOOKINGS",
        )

    try:
        db.delete(unit)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictException(
            detail="Cannot delete unit because booking history exists.",
            error_code="UNIT_HAS_BOOKINGS",
        )
    logger.info("Unit deleted: id=%s", unit_id)

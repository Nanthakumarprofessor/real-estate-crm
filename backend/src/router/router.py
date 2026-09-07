"""
Main API router.

All domain routers are registered here and included into the FastAPI app
in src/main.py under the /api prefix.

Phase 1 : /health endpoint
Phase 3 : /auth  (login + me)
Phase 4+: users, leads, projects, buildings, units, bookings, dashboard
"""
from fastapi import APIRouter

from src.models.api_response_dto import HealthResponse
from src.repository.database import check_database_connection
from src.settings import get_settings

# ── Root API router ───────────────────────────────────────────────────────────
api_router = APIRouter()


# ── Health endpoint ───────────────────────────────────────────────────────────
@api_router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["Health"],
)
def health_check() -> HealthResponse:
    """
    Returns the operational status of the API and its dependencies.

    - **status**: `ok` if the service is running.
    - **database**: `ok` if PostgreSQL is reachable, `unavailable` otherwise.
    - **environment**: current APP_ENV value.
    """
    settings = get_settings()
    db_status = "ok" if check_database_connection() else "unavailable"

    return HealthResponse(
        status="ok",
        database=db_status,
        environment=settings.app_env,
    )


# ── Phase 3: Authentication ───────────────────────────────────────────────────
from src.router.auth_router import router as auth_router          # noqa: E402
api_router.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# ── Phase 4: User Management ──────────────────────────────────────────────────
from src.router.user_router import router as user_router          # noqa: E402
api_router.include_router(user_router, prefix="/users", tags=["Users"])

# ── Phase 5: Lead Management ──────────────────────────────────────────────────
from src.router.lead_router import router as lead_router          # noqa: E402
from src.router.follow_up_router import router as follow_up_router  # noqa: E402
api_router.include_router(lead_router, prefix="/leads", tags=["Leads"])
api_router.include_router(follow_up_router, prefix="/follow-ups", tags=["Follow-ups"])

# ── Phase 6: Property Management ─────────────────────────────────────────────
from src.router.project_router import router as project_router                    # noqa: E402
from src.router.building_router import router as building_router                  # noqa: E402
from src.router.building_router import nested_router as buildings_nested_router   # noqa: E402
from src.router.unit_router import router as unit_router                          # noqa: E402
from src.router.unit_router import nested_router as units_nested_router           # noqa: E402

api_router.include_router(project_router, prefix="/projects", tags=["Projects"])
# Nested: POST/GET /api/projects/{project_id}/buildings
api_router.include_router(
    buildings_nested_router,
    prefix="/projects/{project_id}/buildings",
    tags=["Buildings"],
)
api_router.include_router(building_router, prefix="/buildings", tags=["Buildings"])
# Nested: POST/GET /api/buildings/{building_id}/units
api_router.include_router(
    units_nested_router,
    prefix="/buildings/{building_id}/units",
    tags=["Units"],
)
api_router.include_router(unit_router, prefix="/units", tags=["Units"])

# ── Phase 7: Booking Workflow ─────────────────────────────────────────────────
from src.router.booking_router import router as booking_router    # noqa: E402
api_router.include_router(booking_router, prefix="/bookings", tags=["Bookings"])

# ── Phase 8: Dashboard ───────────────────────────────────────────────────────
from src.router.dashboard_router import router as dashboard_router  # noqa: E402
api_router.include_router(dashboard_router, prefix="/dashboard", tags=["Dashboard"])

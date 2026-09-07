"""
FastAPI application factory.

Responsibilities:
  - Create and configure the FastAPI app instance
  - Register CORS middleware
  - Register global exception handlers
  - Mount the main API router
  - Startup / shutdown lifecycle hooks (via lifespan context manager)
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from src.router.router import api_router
from src.settings import get_settings
from src.utils.exceptions.custom_app_exception import AppException
from src.utils.logger import get_logger

logger = get_logger(__name__)


# ── Lifespan context manager ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Handles application startup and shutdown events.
    Replaces the deprecated @app.on_event("startup"/"shutdown") pattern.
    """
    # ── Startup ───────────────────────────────────────────────────────────────
    settings = get_settings()
    logger.info(
        "Starting Real Estate CRM API | env=%s debug=%s",
        settings.app_env,
        settings.app_debug,
    )
    from src.repository.database import check_database_connection
    if check_database_connection():
        logger.info("Database connection: OK")
    else:
        logger.warning(
            "Database connection: FAILED — "
            "check DATABASE_URL in .env and ensure PostgreSQL is running"
        )

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("Real Estate CRM API shutting down.")


# ── Application factory ───────────────────────────────────────────────────────
def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Real Estate CRM",
        description=(
            "Production-minded Real Estate CRM API. "
            "Manages Leads, Properties, Bookings, and Sales pipeline."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
        # Disable docs in production if needed:
        # docs_url=None if not settings.is_development else "/docs",
    )

    _register_cors(app, settings)
    _register_exception_handlers(app)
    _register_routers(app)

    return app


# ── CORS ──────────────────────────────────────────────────────────────────────
def _register_cors(app: FastAPI, settings) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# ── Exception handlers ────────────────────────────────────────────────────────
def _register_exception_handlers(app: FastAPI) -> None:

    @app.exception_handler(AppException)
    async def app_exception_handler(
        request: Request, exc: AppException
    ) -> JSONResponse:
        """
        Handle all domain/business exceptions raised by services.
        Returns a consistent {detail, error_code} JSON body.
        """
        logger.warning(
            "AppException: status=%s error_code=%s detail=%s path=%s",
            exc.status_code,
            exc.error_code,
            exc.detail,
            request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """
        Handle Pydantic / FastAPI request validation failures.
        Returns HTTP 422 with structured field-level error messages.
        Never exposes internal Python tracebacks.
        """
        errors = exc.errors()
        # Build a readable summary without exposing internals
        messages = []
        for err in errors:
            loc = " → ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "invalid value")
            messages.append(f"{loc}: {msg}" if loc else msg)

        logger.info(
            "Validation error: path=%s errors=%s",
            request.url.path,
            messages,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "detail": "Validation failed.",
                "error_code": "VALIDATION_ERROR",
                "errors": messages,
            },
        )

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(
        request: Request, exc: IntegrityError
    ) -> JSONResponse:
        """
        Catch SQLAlchemy IntegrityError at the outermost boundary.

        This is the safety net for the partial unique index
        `uix_unit_confirmed_booking`. If the booking service's
        SELECT FOR UPDATE somehow fails to catch a duplicate,
        the DB constraint will raise IntegrityError here and
        we return HTTP 409 rather than HTTP 500.

        IMPORTANT: The booking service should already handle this
        before it reaches here. This handler is a last-resort backstop.
        """
        logger.error(
            "IntegrityError caught at handler level: path=%s error=%s",
            request.url.path,
            str(exc.orig) if exc.orig else str(exc),
        )
        # Check if this is a booking uniqueness violation
        error_str = str(exc.orig).lower() if exc.orig else ""
        if "uix_unit_confirmed_booking" in error_str:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "detail": "This unit was just booked by someone else. Please select another unit.",
                    "error_code": "BOOKING_UNIT_ALREADY_BOOKED",
                },
            )
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={
                "detail": "A database conflict occurred.",
                "error_code": "DATABASE_CONFLICT",
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """
        Catch-all for any unhandled exceptions.
        Never exposes stack traces or internal details to the client.
        """
        logger.exception(
            "Unhandled exception: path=%s error=%s",
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An unexpected internal error occurred.",
                "error_code": "INTERNAL_SERVER_ERROR",
            },
        )


# ── Routers ───────────────────────────────────────────────────────────────────
def _register_routers(app: FastAPI) -> None:
    # All routes live under /api
    app.include_router(api_router, prefix="/api")


# ── Module-level app instance (used by uvicorn and tests) ─────────────────────
app = create_app()

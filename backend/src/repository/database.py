"""
Database engine, session factory, and FastAPI dependency.

Uses SQLAlchemy 2.x with psycopg (psycopg3) driver.
All application code should obtain a session via the `get_db` dependency.
"""
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.settings import get_settings


# ── Engine ────────────────────────────────────────────────────────────────────
def _build_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        # Keep a small pool appropriate for a single-server MVP
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,   # recycle stale connections automatically
        echo=settings.is_development,  # log SQL in dev; silent in prod
    )


engine = _build_engine()

# ── Session factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,  # avoid lazy-load issues after commit
)


# ── Declarative base (imported by all ORM models) ─────────────────────────────
class Base(DeclarativeBase):
    pass


# ── FastAPI dependency ────────────────────────────────────────────────────────
def get_db() -> Generator[Session, None, None]:
    """
    Yield a database session for the duration of a request.
    The session is always closed in the finally block, even on error.
    """
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Connection check (used at startup) ───────────────────────────────────────
def check_database_connection() -> bool:
    """
    Attempt a simple SELECT 1 to verify the database is reachable.
    Returns True on success, False on failure.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

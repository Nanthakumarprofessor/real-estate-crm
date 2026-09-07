"""
Alembic environment configuration.

This file is executed by Alembic on every migration command.
It reads DATABASE_URL from the .env file (via src.settings) so
no credentials ever need to be hardcoded in alembic.ini.

Supports:
  - Online migrations (against a live database)
  - Offline migrations (generates SQL scripts without a DB connection)

To run migrations:
    cd backend/
    alembic upgrade head
    alembic downgrade -1
    alembic revision --autogenerate -m "description"
"""
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Make src/ importable from the alembic/ subdirectory ──────────────────────
# Alembic runs from backend/, so backend/ is already on the path.
# This explicit insert ensures src imports work correctly.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Load application settings ─────────────────────────────────────────────────
from src.settings import get_settings  # noqa: E402

settings = get_settings()

# ── Import Base and all ORM models so Alembic can detect schema changes ───────
# schema.py re-exports Base and (in Phase 2+) imports all ORM model classes.
from src.repository.schema import Base  # noqa: E402, F401

# Alembic Config object (wraps alembic.ini)
config = context.config

# Override sqlalchemy.url with the value from .env
config.set_main_option("sqlalchemy.url", settings.database_url)

# Set up Python logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# target_metadata drives --autogenerate diff detection
target_metadata = Base.metadata


# ── Offline mode ──────────────────────────────────────────────────────────────
def run_migrations_offline() -> None:
    """
    Run migrations without an active database connection.
    Generates a SQL script that can be applied manually.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # Render AS with schema-qualified names if using schemas
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode ───────────────────────────────────────────────────────────────
def run_migrations_online() -> None:
    """
    Run migrations against a live database connection.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,  # Use NullPool for migrations (no connection pooling)
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # Compare server defaults (e.g. NOW()) during autogenerate
            compare_server_defaults=True,
        )
        with context.begin_transaction():
            context.run_migrations()


# ── Entry point ───────────────────────────────────────────────────────────────
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

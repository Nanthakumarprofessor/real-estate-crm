"""
Centralised application logger.

Usage:
    from src.utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Lead created", extra={"lead_id": 1})

Rules enforced by convention:
  - Never log passwords, password hashes, or JWT tokens.
  - Never log DATABASE_URL (contains credentials).
  - Log request context (user id, resource id) where helpful.
  - Use structured key=value style in messages for easy grepping.
"""
import logging
import sys
from functools import lru_cache


_LOG_FORMAT = (
    "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger(level: int = logging.INFO) -> None:
    """Configure the root logger once. Subsequent calls are no-ops."""
    root = logging.getLogger()
    if root.handlers:
        # Already configured (e.g. by pytest or uvicorn)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)

    # Silence noisy third-party loggers
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("alembic").setLevel(logging.INFO)


@lru_cache(maxsize=None)
def get_logger(name: str) -> logging.Logger:
    """
    Return a named logger.
    The root logger is configured on first call.
    """
    _configure_root_logger()
    return logging.getLogger(name)

"""System Design Interview Simulator - Database Package.

Exposes SQLAlchemy DeclarativeBase, async engine, session makers, model mixins,
FastAPI session dependencies, and health check utilities.
"""

from app.db.base import Base, POSTGRES_NAMING_CONVENTION
from app.db.deps import get_db
from app.db.health import check_db_health
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.db.session import (
    async_session_factory,
    engine,
    get_async_session_context,
)
from app.db.utils import async_transaction

__all__ = [
    "Base",
    "POSTGRES_NAMING_CONVENTION",
    "SoftDeleteMixin",
    "TimestampMixin",
    "UUIDPrimaryKeyMixin",
    "async_session_factory",
    "async_transaction",
    "check_db_health",
    "engine",
    "get_async_session_context",
    "get_db",
]

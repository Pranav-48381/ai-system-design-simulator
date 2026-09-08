"""System Design Interview Simulator - SQLAlchemy Declarative Base.

Defines SQLAlchemy 2.0 DeclarativeBase configured with standardized database
naming conventions for constraints, foreign keys, and indexes.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Standardized constraint naming conventions required for consistent Alembic migrations
POSTGRES_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Base declarative class for all SQLAlchemy ORM models."""

    metadata = MetaData(naming_convention=POSTGRES_NAMING_CONVENTION)

    def __repr__(self) -> str:
        """Generic string representation showing class name and primary key attributes."""
        attrs = []
        for key in self.__mapper__.column_attrs.keys():
            if "password" in key or "token" in key or "secret" in key:
                continue
            attrs.append(f"{key}={getattr(self, key)!r}")
        return f"<{self.__class__.__name__}({', '.join(attrs[:4])})>"

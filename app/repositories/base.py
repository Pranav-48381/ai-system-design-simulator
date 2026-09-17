"""System Design Interview Simulator - Generic Base Repository.

Provides a robust, type-safe, asynchronous generic repository pattern implementation
built on SQLAlchemy 2.0 and AsyncSession, standardizing CRUD operations and pagination.
"""

from collections.abc import Sequence
from typing import Any, Generic, TypeVar
import uuid

from sqlalchemy import BinaryExpression, ColumnElement, delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.db.base import Base
from app.schemas.common import PaginationMeta, PaginationParams

logger = get_logger(__name__)

# Generic model type bound to SQLAlchemy Declarative Base
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Generic async repository providing standard data access operations."""

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        """Initialize repository with target entity model class and active database session.

        Args:
            model: The SQLAlchemy Declarative model class.
            session: Active SQLAlchemy AsyncSession.
        """
        self._model = model
        self._session = session

    @property
    def model(self) -> type[ModelType]:
        """Return the managed SQLAlchemy Declarative entity model class."""
        return self._model

    @property
    def session(self) -> AsyncSession:
        """Return the underlying active asynchronous database session."""
        return self._session

    async def get_by_id(self, entity_id: uuid.UUID | str | int) -> ModelType | None:
        """Retrieve a single entity by its primary key identifier.

        Args:
            entity_id: Primary key value (UUID, string, or integer).

        Returns:
            The entity instance if found, or None.
        """
        stmt = select(self._model).where(self._model.id == entity_id)  # type: ignore[attr-defined]
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_raise(self, entity_id: uuid.UUID | str | int) -> ModelType:
        """Retrieve a single entity by ID or raise EntityNotFoundError if missing.

        Args:
            entity_id: Primary key value.

        Returns:
            The persisted entity instance.

        Raises:
            EntityNotFoundError: If no record with the given ID exists.
        """
        instance = await self.get_by_id(entity_id)
        if instance is None:
            raise EntityNotFoundError(
                entity_name=self._model.__name__,
                entity_id=entity_id,
            )
        return instance

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Sequence[ColumnElement[bool] | BinaryExpression] | None = None,
        order_by: Any = None,
    ) -> Sequence[ModelType]:
        """Query a collection of entities matching optional criteria.

        Args:
            skip: Number of records to skip (OFFSET).
            limit: Maximum number of records to return (LIMIT).
            filters: Optional sequence of SQLAlchemy filter expressions.
            order_by: Optional ordering clause (e.g., Model.created_at.desc()).

        Returns:
            Sequence of matched entity instances.
        """
        stmt = select(self._model)
        if filters:
            for clause in filters:
                stmt = stmt.where(clause)

        if order_by is not None:
            stmt = stmt.order_by(order_by)
        elif hasattr(self._model, "created_at"):
            stmt = stmt.order_by(getattr(self._model, "created_at").desc())

        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count(
        self,
        filters: Sequence[ColumnElement[bool] | BinaryExpression] | None = None,
    ) -> int:
        """Calculate total number of records matching optional filters.

        Args:
            filters: Optional filter expressions.

        Returns:
            Total integer count.
        """
        stmt = select(func.count()).select_from(self._model)
        if filters:
            for clause in filters:
                stmt = stmt.where(clause)
        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def exists(self, entity_id: uuid.UUID | str | int) -> bool:
        """Check whether a record with the specified ID exists in the database.

        Args:
            entity_id: Primary key to check.

        Returns:
            True if entity exists, False otherwise.
        """
        stmt = (
            select(func.count())
            .select_from(self._model)
            .where(self._model.id == entity_id)  # type: ignore[attr-defined]
        )
        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def create(self, instance: ModelType, flush: bool = True) -> ModelType:
        """Persist a new model instance into the database session.

        Args:
            instance: Entity instance to persist.
            flush: Whether to flush session immediately to populate defaults and IDs.

        Returns:
            The persisted model instance.
        """
        self._session.add(instance)
        if flush:
            await self._session.flush()
            await self._session.refresh(instance)
        return instance

    async def create_many(
        self,
        instances: Sequence[ModelType],
        flush: bool = True,
    ) -> Sequence[ModelType]:
        """Persist a batch of model instances.

        Args:
            instances: Collection of model entities to add.
            flush: Whether to execute session flush immediately.

        Returns:
            The sequence of persisted entities.
        """
        self._session.add_all(instances)
        if flush:
            await self._session.flush()
        return instances

    async def update(self, instance: ModelType, flush: bool = True) -> ModelType:
        """Update and synchronize an existing model instance in the session.

        Args:
            instance: Entity instance with modified fields.
            flush: Whether to flush session immediately.

        Returns:
            The updated model instance.
        """
        merged_instance = await self._session.merge(instance)
        if flush:
            await self._session.flush()
            await self._session.refresh(merged_instance)
        return merged_instance

    async def delete(self, instance: ModelType, flush: bool = True) -> None:
        """Delete an existing entity instance from the database.

        Args:
            instance: The model instance to remove.
            flush: Whether to flush changes immediately.
        """
        await self._session.delete(instance)
        if flush:
            await self._session.flush()

    async def delete_by_id(self, entity_id: uuid.UUID | str | int, flush: bool = True) -> bool:
        """Delete an entity by its primary key identifier.

        Args:
            entity_id: Primary key of entity to delete.
            flush: Whether to flush session immediately.

        Returns:
            True if entity was found and deleted, False otherwise.
        """
        instance = await self.get_by_id(entity_id)
        if instance is None:
            return False
        await self.delete(instance, flush=flush)
        return True

    async def paginate(
        self,
        params: PaginationParams,
        filters: Sequence[ColumnElement[bool] | BinaryExpression] | None = None,
        order_by: Any = None,
    ) -> tuple[Sequence[ModelType], PaginationMeta]:
        """Execute a paginated query returning items and associated pagination metadata.

        Args:
            params: Pagination parameters (page, page_size).
            filters: Optional query filter clauses.
            order_by: Optional order by clause.

        Returns:
            A tuple of (items_sequence, pagination_metadata).
        """
        total_items = await self.count(filters=filters)
        items = await self.list_all(
            skip=params.offset,
            limit=params.limit,
            filters=filters,
            order_by=order_by,
        )
        meta = PaginationMeta.create(
            page=params.page,
            page_size=params.page_size,
            total_items=total_items,
        )
        return items, meta

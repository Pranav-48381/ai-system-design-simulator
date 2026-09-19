"""System Design Interview Simulator - Rubric Repository.

Provides specialized asynchronous data access operations for evaluation rubrics,
including rubric blueprints, 5-pillar competency criteria, seniority level expectations,
and default rubric resolution for new interview sessions.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ScoringPillar
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.rubric import EvaluationRubric, RubricCriterion
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class RubricRepository(BaseRepository[EvaluationRubric]):
    """Repository handling evaluation rubric blueprints and competency criteria."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize RubricRepository with active AsyncSession."""
        super().__init__(EvaluationRubric, session)

    async def get_by_id(
        self,
        rubric_id: uuid.UUID,
        load_criteria: bool = True,
    ) -> EvaluationRubric | None:
        """Retrieve evaluation rubric by unique identifier with optional criteria loading.

        Args:
            rubric_id: EvaluationRubric UUID.
            load_criteria: Whether to eagerly load criteria.

        Returns:
            The EvaluationRubric instance, or None if not found.
        """
        stmt = select(EvaluationRubric).where(EvaluationRubric.id == rubric_id)
        if load_criteria:
            stmt = stmt.options(selectinload(EvaluationRubric.criteria))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_raise(
        self,
        rubric_id: uuid.UUID,
        load_criteria: bool = True,
    ) -> EvaluationRubric:
        """Retrieve evaluation rubric by ID or raise EntityNotFoundError.

        Args:
            rubric_id: EvaluationRubric UUID.
            load_criteria: Whether to eagerly load criteria.

        Returns:
            The EvaluationRubric instance.

        Raises:
            EntityNotFoundError: If rubric does not exist.
        """
        rubric = await self.get_by_id(rubric_id, load_criteria=load_criteria)
        if rubric is None:
            raise EntityNotFoundError(
                entity_name="EvaluationRubric",
                entity_id=rubric_id,
            )
        return rubric

    async def get_by_name(
        self,
        name: str,
        load_criteria: bool = True,
    ) -> EvaluationRubric | None:
        """Retrieve evaluation rubric by unique human-readable name.

        Args:
            name: Rubric name string.
            load_criteria: Whether to eagerly load criteria.

        Returns:
            The EvaluationRubric instance, or None.
        """
        stmt = select(EvaluationRubric).where(
            func.lower(EvaluationRubric.name) == name.strip().lower()
        )
        if load_criteria:
            stmt = stmt.options(selectinload(EvaluationRubric.criteria))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_rubric(
        self,
        load_criteria: bool = True,
    ) -> EvaluationRubric | None:
        """Retrieve the system-wide default evaluation rubric.

        Args:
            load_criteria: Whether to eagerly load criteria.

        Returns:
            The default EvaluationRubric instance, or None if not configured.
        """
        stmt = select(EvaluationRubric).where(EvaluationRubric.is_default.is_(True))
        if load_criteria:
            stmt = stmt.options(selectinload(EvaluationRubric.criteria))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_default_or_raise(
        self,
        load_criteria: bool = True,
    ) -> EvaluationRubric:
        """Retrieve the system-wide default rubric or raise EntityNotFoundError.

        Args:
            load_criteria: Whether to eagerly load criteria.

        Returns:
            The default EvaluationRubric instance.

        Raises:
            EntityNotFoundError: If no default rubric exists in the database.
        """
        rubric = await self.get_default_rubric(load_criteria=load_criteria)
        if rubric is None:
            raise EntityNotFoundError(
                entity_name="EvaluationRubric",
                entity_id="default",
            )
        return rubric

    async def list_rubrics(
        self,
        skip: int = 0,
        limit: int = 50,
        load_criteria: bool = False,
    ) -> Sequence[EvaluationRubric]:
        """Query a paginated collection of evaluation rubrics.

        Args:
            skip: Number of records to skip.
            limit: Maximum records to return.
            load_criteria: Whether to eagerly load criteria.

        Returns:
            Sequence of EvaluationRubric instances ordered by created_at desc.
        """
        stmt = (
            select(EvaluationRubric)
            .order_by(EvaluationRubric.is_default.desc(), EvaluationRubric.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if load_criteria:
            stmt = stmt.options(selectinload(EvaluationRubric.criteria))

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def create_rubric(
        self,
        name: str,
        description: str,
        is_default: bool = False,
        criteria: Sequence[dict[str, Any]] | None = None,
        flush: bool = True,
    ) -> EvaluationRubric:
        """Create and persist a new evaluation rubric blueprint with optional criteria.

        Args:
            name: Unique name of the rubric.
            description: Detailed description of scoring methodology.
            is_default: Whether to mark this rubric as the default framework.
            criteria: Optional initial list of criteria definitions.
            flush: Whether to execute session flush immediately.

        Returns:
            The newly created EvaluationRubric instance.
        """
        if is_default:
            # Unset any existing default rubric
            await self._unset_existing_defaults()

        rubric = EvaluationRubric(
            name=name.strip(),
            description=description.strip(),
            is_default=is_default,
        )

        if criteria:
            for item in criteria:
                rubric.criteria.append(
                    RubricCriterion(
                        pillar=item["pillar"],
                        title=str(item["title"]).strip(),
                        description=str(item["description"]).strip(),
                        weight=float(item.get("weight", 1.0)),
                        level_expectations=item.get("level_expectations", {}),
                    )
                )

        created = await self.create(rubric, flush=flush)
        logger.info(
            "Created rubric '%s' (id: %s, criteria: %d, default: %s)",
            created.name,
            created.id,
            len(created.criteria),
            created.is_default,
        )
        return created

    async def set_default_rubric(
        self,
        rubric_id: uuid.UUID,
        flush: bool = True,
    ) -> EvaluationRubric:
        """Set a specific rubric as the default, unsetting all others.

        Args:
            rubric_id: Target EvaluationRubric UUID.
            flush: Whether to execute session flush immediately.

        Returns:
            The updated default EvaluationRubric.
        """
        rubric = await self.get_or_raise(rubric_id, load_criteria=False)
        await self._unset_existing_defaults()
        rubric.is_default = True
        if flush:
            await self._session.flush()
            await self._session.refresh(rubric)

        logger.info("Set rubric %s ('%s') as the system default", rubric.id, rubric.name)
        return rubric

    async def update_rubric(
        self,
        rubric_id: uuid.UUID,
        name: str | None = None,
        description: str | None = None,
        is_default: bool | None = None,
        flush: bool = True,
    ) -> EvaluationRubric:
        """Update metadata for an existing evaluation rubric.

        Args:
            rubric_id: Target EvaluationRubric UUID.
            name: Optional new unique name.
            description: Optional new description.
            is_default: Optional default flag change.
            flush: Whether to execute session flush immediately.

        Returns:
            The updated EvaluationRubric instance.
        """
        rubric = await self.get_or_raise(rubric_id, load_criteria=False)
        if name is not None:
            rubric.name = name.strip()
        if description is not None:
            rubric.description = description.strip()
        if is_default is not None:
            if is_default:
                await self._unset_existing_defaults()
            rubric.is_default = is_default

        if flush:
            await self._session.flush()
            await self._session.refresh(rubric)

        logger.info("Updated rubric %s ('%s')", rubric.id, rubric.name)
        return rubric

    async def add_criterion(
        self,
        rubric_id: uuid.UUID,
        pillar: ScoringPillar,
        title: str,
        description: str,
        weight: float = 1.0,
        level_expectations: dict[str, Any] | None = None,
        flush: bool = True,
    ) -> RubricCriterion:
        """Add a new scoring criterion to an existing evaluation rubric.

        Args:
            rubric_id: Target EvaluationRubric UUID.
            pillar: Evaluation pillar category.
            title: Title of capability being evaluated.
            description: Benchmark definition of excellence.
            weight: Relative weight multiplier.
            level_expectations: Expectations mapped by seniority level.
            flush: Whether to execute session flush immediately.

        Returns:
            The created RubricCriterion entity.
        """
        # Ensure parent rubric exists
        await self.get_or_raise(rubric_id, load_criteria=False)

        criterion = RubricCriterion(
            rubric_id=rubric_id,
            pillar=pillar,
            title=title.strip(),
            description=description.strip(),
            weight=weight,
            level_expectations=level_expectations or {},
        )
        self._session.add(criterion)
        if flush:
            await self._session.flush()
            await self._session.refresh(criterion)

        logger.info(
            "Added criterion '%s' (%s) to rubric %s",
            criterion.title,
            pillar.value,
            rubric_id,
        )
        return criterion

    async def get_criterion(self, criterion_id: uuid.UUID) -> RubricCriterion | None:
        """Retrieve a specific rubric criterion by its identifier.

        Args:
            criterion_id: RubricCriterion UUID.

        Returns:
            The RubricCriterion instance, or None.
        """
        stmt = select(RubricCriterion).where(RubricCriterion.id == criterion_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_criteria_by_pillar(
        self,
        rubric_id: uuid.UUID,
        pillar: ScoringPillar,
    ) -> Sequence[RubricCriterion]:
        """Retrieve all criteria belonging to a specific pillar for a rubric.

        Args:
            rubric_id: Target EvaluationRubric UUID.
            pillar: Target ScoringPillar.

        Returns:
            Sequence of RubricCriterion instances.
        """
        stmt = (
            select(RubricCriterion)
            .where(
                RubricCriterion.rubric_id == rubric_id,
                RubricCriterion.pillar == pillar,
            )
            .order_by(RubricCriterion.title.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def delete_criterion(
        self,
        criterion_id: uuid.UUID,
        flush: bool = True,
    ) -> bool:
        """Delete a criterion by identifier.

        Args:
            criterion_id: RubricCriterion UUID.
            flush: Whether to execute session flush immediately.

        Returns:
            True if deleted, False if not found.
        """
        criterion = await self.get_criterion(criterion_id)
        if criterion is None:
            return False

        await self._session.delete(criterion)
        if flush:
            await self._session.flush()
        logger.info("Deleted criterion %s", criterion_id)
        return True

    async def count_rubrics(self) -> int:
        """Count total evaluation rubrics in the system.

        Returns:
            Total integer count.
        """
        return await self.count()

    async def _unset_existing_defaults(self) -> None:
        """Internal helper to unset is_default on all rubrics."""
        stmt = (
            sql_update(EvaluationRubric)
            .where(EvaluationRubric.is_default.is_(True))
            .values(is_default=False)
        )
        await self._session.execute(stmt)

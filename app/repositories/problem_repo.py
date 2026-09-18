"""System Design Interview Simulator - Problem Repository.

Provides specialized asynchronous data access operations for system design interview problems,
including slug retrieval, difficulty filtering, tag associations, and full-text search.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import ProblemDifficulty
from app.core.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from app.core.logging import get_logger
from app.models.problem import SystemDesignProblem
from app.models.tag import ProblemTag
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ProblemRepository(BaseRepository[SystemDesignProblem]):
    """Repository handling persistence, filtering, and tag management for SystemDesignProblem."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ProblemRepository with active AsyncSession."""
        super().__init__(SystemDesignProblem, session)

    async def get_by_slug(
        self,
        slug: str,
        include_inactive: bool = False,
        include_deleted: bool = False,
        load_tags: bool = True,
    ) -> SystemDesignProblem | None:
        """Query a problem by its unique URL slug.

        Args:
            slug: URL slug identifying the problem.
            include_inactive: Whether to return inactive problems.
            include_deleted: Whether to include soft-deleted problems.
            load_tags: Whether to eagerly load associated classification tags.

        Returns:
            The SystemDesignProblem instance if found, or None.
        """
        normalized_slug = slug.strip().lower()
        stmt = select(SystemDesignProblem).where(func.lower(SystemDesignProblem.slug) == normalized_slug)

        if not include_deleted:
            stmt = stmt.where(SystemDesignProblem.is_deleted.is_(False))
        if not include_inactive:
            stmt = stmt.where(SystemDesignProblem.is_active.is_(True))

        if load_tags:
            stmt = stmt.options(selectinload(SystemDesignProblem.tags))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug_or_raise(
        self,
        slug: str,
        include_inactive: bool = False,
        include_deleted: bool = False,
        load_tags: bool = True,
    ) -> SystemDesignProblem:
        """Query a problem by slug or raise EntityNotFoundError if not found.

        Args:
            slug: URL slug identifying the problem.
            include_inactive: Whether to return inactive problems.
            include_deleted: Whether to include soft-deleted problems.
            load_tags: Whether to eagerly load associated classification tags.

        Returns:
            The persisted SystemDesignProblem instance.

        Raises:
            EntityNotFoundError: If no matching problem exists.
        """
        problem = await self.get_by_slug(
            slug=slug,
            include_inactive=include_inactive,
            include_deleted=include_deleted,
            load_tags=load_tags,
        )
        if problem is None:
            raise EntityNotFoundError(entity_name="SystemDesignProblem", entity_id=slug)
        return problem

    async def slug_exists(
        self,
        slug: str,
        exclude_problem_id: uuid.UUID | None = None,
    ) -> bool:
        """Check whether a problem slug is already taken.

        Args:
            slug: Slug string to check.
            exclude_problem_id: Optional problem UUID to exclude from check.

        Returns:
            True if slug exists, False otherwise.
        """
        normalized_slug = slug.strip().lower()
        stmt = select(func.count()).select_from(SystemDesignProblem).where(
            func.lower(SystemDesignProblem.slug) == normalized_slug,
            SystemDesignProblem.is_deleted.is_(False),
        )
        if exclude_problem_id is not None:
            stmt = stmt.where(SystemDesignProblem.id != exclude_problem_id)

        result = await self._session.execute(stmt)
        return (result.scalar_one() or 0) > 0

    async def get_by_id_with_tags(
        self,
        problem_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> SystemDesignProblem | None:
        """Retrieve a problem by primary key with eagerly loaded tags.

        Args:
            problem_id: UUID of the problem.
            include_deleted: Whether to include soft-deleted problems.

        Returns:
            The SystemDesignProblem instance with loaded tags, or None.
        """
        stmt = (
            select(SystemDesignProblem)
            .where(SystemDesignProblem.id == problem_id)
            .options(selectinload(SystemDesignProblem.tags))
        )
        if not include_deleted:
            stmt = stmt.where(SystemDesignProblem.is_deleted.is_(False))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_difficulty(
        self,
        difficulty: ProblemDifficulty,
        skip: int = 0,
        limit: int = 100,
        load_tags: bool = True,
    ) -> Sequence[SystemDesignProblem]:
        """Query active problems matching a specific difficulty tier.

        Args:
            difficulty: ProblemDifficulty level (BEGINNER, MEDIUM, ADVANCED).
            skip: Offset number of records.
            limit: Maximum number of records.
            load_tags: Whether to eagerly load tags.

        Returns:
            Sequence of matching problems.
        """
        stmt = (
            select(SystemDesignProblem)
            .where(
                SystemDesignProblem.difficulty == difficulty,
                SystemDesignProblem.is_active.is_(True),
                SystemDesignProblem.is_deleted.is_(False),
            )
            .order_by(SystemDesignProblem.title.asc())
            .offset(skip)
            .limit(limit)
        )
        if load_tags:
            stmt = stmt.options(selectinload(SystemDesignProblem.tags))

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_tag(
        self,
        tag_name: str,
        skip: int = 0,
        limit: int = 100,
        load_tags: bool = True,
    ) -> Sequence[SystemDesignProblem]:
        """Query active problems associated with a specific tag name.

        Args:
            tag_name: Classification tag name (e.g. 'caching', 'distributed-systems').
            skip: Offset number of records.
            limit: Maximum number of records.
            load_tags: Whether to eagerly load tags.

        Returns:
            Sequence of problems containing the given tag.
        """
        normalized_tag = tag_name.strip().lower()
        stmt = (
            select(SystemDesignProblem)
            .join(SystemDesignProblem.tags)
            .where(
                func.lower(ProblemTag.name) == normalized_tag,
                SystemDesignProblem.is_active.is_(True),
                SystemDesignProblem.is_deleted.is_(False),
            )
            .order_by(SystemDesignProblem.title.asc())
            .offset(skip)
            .limit(limit)
        )
        if load_tags:
            stmt = stmt.options(selectinload(SystemDesignProblem.tags))

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def filter_problems(
        self,
        difficulty: ProblemDifficulty | None = None,
        tag_name: str | None = None,
        search_query: str | None = None,
        is_active: bool | None = True,
        include_deleted: bool = False,
        skip: int = 0,
        limit: int = 100,
        load_tags: bool = True,
    ) -> tuple[Sequence[SystemDesignProblem], int]:
        """Filter and search problems with pagination and total count.

        Args:
            difficulty: Optional difficulty filter.
            tag_name: Optional tag classification filter.
            search_query: Optional substring search query on title or summary.
            is_active: Filter by active status (or None for all).
            include_deleted: Whether to include soft-deleted records.
            skip: Offset.
            limit: Page size limit.
            load_tags: Whether to eagerly load tags.

        Returns:
            Tuple of (matched_problems_sequence, total_count).
        """
        stmt = select(SystemDesignProblem)
        count_stmt = select(func.count(SystemDesignProblem.id.distinct()))

        if tag_name:
            normalized_tag = tag_name.strip().lower()
            stmt = stmt.join(SystemDesignProblem.tags).where(func.lower(ProblemTag.name) == normalized_tag)
            count_stmt = count_stmt.join(SystemDesignProblem.tags).where(func.lower(ProblemTag.name) == normalized_tag)

        if not include_deleted:
            stmt = stmt.where(SystemDesignProblem.is_deleted.is_(False))
            count_stmt = count_stmt.where(SystemDesignProblem.is_deleted.is_(False))

        if is_active is not None:
            stmt = stmt.where(SystemDesignProblem.is_active.is_(is_active))
            count_stmt = count_stmt.where(SystemDesignProblem.is_active.is_(is_active))

        if difficulty is not None:
            stmt = stmt.where(SystemDesignProblem.difficulty == difficulty)
            count_stmt = count_stmt.where(SystemDesignProblem.difficulty == difficulty)

        if search_query:
            term = f"%{search_query.strip()}%"
            search_filter = or_(
                SystemDesignProblem.title.ilike(term),
                SystemDesignProblem.summary.ilike(term),
                SystemDesignProblem.description.ilike(term),
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        if load_tags:
            stmt = stmt.options(selectinload(SystemDesignProblem.tags))

        stmt = stmt.order_by(SystemDesignProblem.title.asc()).offset(skip).limit(limit)

        total_res = await self._session.execute(count_stmt)
        total = total_res.scalar_one() or 0

        items_res = await self._session.execute(stmt)
        items = items_res.scalars().all()

        return items, total

    async def get_random_problem(
        self,
        difficulty: ProblemDifficulty | None = None,
        load_tags: bool = True,
    ) -> SystemDesignProblem | None:
        """Retrieve a random active problem, optionally filtered by difficulty.

        Args:
            difficulty: Optional target difficulty.
            load_tags: Whether to eagerly load tags.

        Returns:
            A random SystemDesignProblem instance or None if no problems match.
        """
        stmt = (
            select(SystemDesignProblem)
            .where(
                SystemDesignProblem.is_active.is_(True),
                SystemDesignProblem.is_deleted.is_(False),
            )
            .order_by(func.random())
            .limit(1)
        )
        if difficulty is not None:
            stmt = stmt.where(SystemDesignProblem.difficulty == difficulty)
        if load_tags:
            stmt = stmt.options(selectinload(SystemDesignProblem.tags))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_problem(
        self,
        slug: str,
        title: str,
        summary: str,
        description: str,
        difficulty: ProblemDifficulty = ProblemDifficulty.MEDIUM,
        functional_requirements: list[str] | None = None,
        non_functional_requirements: list[str] | None = None,
        scale_targets: dict[str, Any] | None = None,
        key_challenges: list[str] | None = None,
        reference_solution: dict[str, Any] | None = None,
        tag_names: list[str] | None = None,
        is_active: bool = True,
    ) -> SystemDesignProblem:
        """Create and persist a new system design problem definition.

        Args:
            slug: Unique URL slug identifier.
            title: Challenge title.
            summary: Short description summary.
            description: Complete problem statement.
            difficulty: Difficulty tier.
            functional_requirements: List of core functional specs.
            non_functional_requirements: List of availability/latency/scale specs.
            scale_targets: Capacity estimations and targets dictionary.
            key_challenges: List of tricky architectural trade-offs.
            reference_solution: Optional blueprint architectural reference.
            tag_names: Optional tag strings to associate.
            is_active: Whether problem is available for interviews.

        Returns:
            The created SystemDesignProblem instance.

        Raises:
            EntityAlreadyExistsError: If slug is already registered.
        """
        normalized_slug = slug.strip().lower()
        if await self.slug_exists(normalized_slug):
            logger.warning("Attempted problem creation with existing slug: %s", normalized_slug)
            raise EntityAlreadyExistsError(entity_name="SystemDesignProblem", identifier=normalized_slug)

        problem = SystemDesignProblem(
            slug=normalized_slug,
            title=title.strip(),
            summary=summary.strip(),
            description=description.strip(),
            difficulty=difficulty,
            functional_requirements=functional_requirements or [],
            non_functional_requirements=non_functional_requirements or [],
            scale_targets=scale_targets or {},
            key_challenges=key_challenges or [],
            reference_solution=reference_solution,
            is_active=is_active,
        )

        if tag_names:
            tags = await self._resolve_or_create_tags(tag_names)
            problem.tags = tags

        created_problem = await self.create(problem, flush=True)
        logger.info("Created system design problem: '%s' (id: %s)", created_problem.slug, created_problem.id)
        return created_problem

    async def _resolve_or_create_tags(self, tag_names: list[str]) -> list[ProblemTag]:
        """Resolve existing tags or create new tags in the database.

        Args:
            tag_names: List of tag name strings.

        Returns:
            List of ProblemTag model instances.
        """
        resolved_tags: list[ProblemTag] = []
        for name in tag_names:
            normalized_name = name.strip().lower()
            if not normalized_name:
                continue

            stmt = select(ProblemTag).where(func.lower(ProblemTag.name) == normalized_name)
            res = await self._session.execute(stmt)
            tag = res.scalar_one_or_none()

            if tag is None:
                tag = ProblemTag(name=normalized_name)
                self._session.add(tag)
                await self._session.flush()
                await self._session.refresh(tag)

            resolved_tags.append(tag)

        return resolved_tags

    async def soft_delete(self, problem_id: uuid.UUID) -> bool:
        """Soft delete a problem by setting is_deleted=True.

        Args:
            problem_id: UUID of problem to delete.

        Returns:
            True if problem was soft-deleted, False if not found.
        """
        problem = await self.get_by_id(problem_id)
        if problem is None or problem.is_deleted:
            return False

        problem.is_deleted = True
        problem.deleted_at = datetime.now(timezone.utc)
        problem.is_active = False
        await self._session.flush()
        logger.info("SystemDesignProblem %s soft-deleted successfully", problem_id)
        return True

    async def restore(self, problem_id: uuid.UUID) -> bool:
        """Restore a previously soft-deleted problem.

        Args:
            problem_id: UUID of problem to restore.

        Returns:
            True if restored, False if not found or not deleted.
        """
        stmt = select(SystemDesignProblem).where(
            SystemDesignProblem.id == problem_id,
            SystemDesignProblem.is_deleted.is_(True),
        )
        result = await self._session.execute(stmt)
        problem = result.scalar_one_or_none()
        if problem is None:
            return False

        problem.is_deleted = False
        problem.deleted_at = None
        problem.is_active = True
        await self._session.flush()
        logger.info("SystemDesignProblem %s restored successfully", problem_id)
        return True

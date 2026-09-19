"""System Design Interview Simulator - Feedback Repository.

Provides specialized asynchronous data access operations for interview evaluation feedback items,
including category-based queries (strengths, improvements, critical gaps, recommendations),
pillar alignment, bulk creation, and summary metrics.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ScoringPillar
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.enums import FeedbackCategory
from app.models.feedback import EvaluationFeedbackItem
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class FeedbackRepository(BaseRepository[EvaluationFeedbackItem]):
    """Repository handling structured observations, strengths, gaps, and study resources."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize FeedbackRepository with active AsyncSession."""
        super().__init__(EvaluationFeedbackItem, session)

    async def list_by_evaluation(
        self,
        evaluation_id: uuid.UUID,
        category: FeedbackCategory | None = None,
        pillar: ScoringPillar | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[EvaluationFeedbackItem]:
        """Query feedback items associated with a specific evaluation scorecard.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.
            category: Optional FeedbackCategory filter.
            pillar: Optional ScoringPillar filter.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.

        Returns:
            Sequence of EvaluationFeedbackItem instances ordered by created_at.
        """
        stmt = select(EvaluationFeedbackItem).where(
            EvaluationFeedbackItem.evaluation_id == evaluation_id
        )
        if category is not None:
            stmt = stmt.where(EvaluationFeedbackItem.category == category)
        if pillar is not None:
            stmt = stmt.where(EvaluationFeedbackItem.pillar == pillar)

        stmt = stmt.order_by(EvaluationFeedbackItem.created_at.asc()).offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_by_category(
        self,
        evaluation_id: uuid.UUID,
        category: FeedbackCategory,
    ) -> Sequence[EvaluationFeedbackItem]:
        """Retrieve feedback items filtered by a specific feedback category.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.
            category: Target FeedbackCategory.

        Returns:
            Sequence of matching EvaluationFeedbackItem instances.
        """
        return await self.list_by_evaluation(evaluation_id=evaluation_id, category=category)

    async def list_strengths(self, evaluation_id: uuid.UUID) -> Sequence[EvaluationFeedbackItem]:
        """Retrieve all positive strength feedback items for an evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Sequence of strength feedback items.
        """
        return await self.list_by_category(evaluation_id, FeedbackCategory.STRENGTH)

    async def list_improvements(self, evaluation_id: uuid.UUID) -> Sequence[EvaluationFeedbackItem]:
        """Retrieve all improvement areas for an evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Sequence of improvement feedback items.
        """
        return await self.list_by_category(evaluation_id, FeedbackCategory.IMPROVEMENT)

    async def list_critical_gaps(self, evaluation_id: uuid.UUID) -> Sequence[EvaluationFeedbackItem]:
        """Retrieve all critical architecture and design gaps for an evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Sequence of critical gap feedback items.
        """
        return await self.list_by_category(evaluation_id, FeedbackCategory.CRITICAL_GAP)

    async def list_recommendations(self, evaluation_id: uuid.UUID) -> Sequence[EvaluationFeedbackItem]:
        """Retrieve all recommended reading and study guidelines for an evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Sequence of recommendation feedback items.
        """
        return await self.list_by_category(evaluation_id, FeedbackCategory.RECOMMENDATION)

    async def create_feedback_item(
        self,
        evaluation_id: uuid.UUID,
        category: FeedbackCategory,
        title: str,
        detail: str,
        pillar: ScoringPillar | None = None,
        resources: list[dict[str, Any]] | None = None,
        flush: bool = True,
    ) -> EvaluationFeedbackItem:
        """Create and persist a single feedback item for an interview evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.
            category: Classification of observation.
            title: Concise summary title of the feedback point.
            detail: In-depth explanation of the observation.
            pillar: Optional architecture pillar aligned with this observation.
            resources: Optional recommended learning links and articles.
            flush: Whether to execute session flush immediately.

        Returns:
            The newly created EvaluationFeedbackItem instance.
        """
        item = EvaluationFeedbackItem(
            evaluation_id=evaluation_id,
            category=category,
            title=title.strip(),
            detail=detail.strip(),
            pillar=pillar,
            resources=resources or [],
        )
        created = await self.create(item, flush=flush)
        logger.info(
            "Created feedback item %s (%s) for evaluation %s",
            created.id,
            category.value,
            evaluation_id,
        )
        return created

    async def create_batch(
        self,
        evaluation_id: uuid.UUID,
        items: Sequence[dict[str, Any]],
        flush: bool = True,
    ) -> Sequence[EvaluationFeedbackItem]:
        """Persist multiple structured feedback observations in a single batch.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.
            items: Sequence of dictionaries containing feedback payload attributes.
            flush: Whether to execute session flush immediately.

        Returns:
            The sequence of persisted EvaluationFeedbackItem entities.
        """
        instances: list[EvaluationFeedbackItem] = []
        for raw in items:
            instances.append(
                EvaluationFeedbackItem(
                    evaluation_id=evaluation_id,
                    category=raw.get("category", FeedbackCategory.IMPROVEMENT),
                    title=str(raw.get("title", "")).strip(),
                    detail=str(raw.get("detail", "")).strip(),
                    pillar=raw.get("pillar"),
                    resources=raw.get("resources", []),
                )
            )

        persisted = await self.create_many(instances, flush=flush)
        logger.info(
            "Batch-created %d feedback items for evaluation %s",
            len(persisted),
            evaluation_id,
        )
        return persisted

    async def delete_by_evaluation(
        self,
        evaluation_id: uuid.UUID,
        flush: bool = True,
    ) -> int:
        """Delete all feedback items associated with a given evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.
            flush: Whether to execute session flush immediately.

        Returns:
            The number of records deleted.
        """
        stmt = (
            sql_delete(EvaluationFeedbackItem)
            .where(EvaluationFeedbackItem.evaluation_id == evaluation_id)
        )
        result = await self._session.execute(stmt)
        if flush:
            await self._session.flush()
        deleted_count = result.rowcount or 0
        logger.info(
            "Deleted %d feedback items for evaluation %s",
            deleted_count,
            evaluation_id,
        )
        return deleted_count

    async def count_by_category(self, evaluation_id: uuid.UUID) -> dict[str, int]:
        """Calculate counts of feedback items grouped by feedback category.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Dictionary mapping category string values to integer counts.
        """
        stmt = (
            select(EvaluationFeedbackItem.category, func.count())
            .where(EvaluationFeedbackItem.evaluation_id == evaluation_id)
            .group_by(EvaluationFeedbackItem.category)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        counts: dict[str, int] = {cat.value: 0 for cat in FeedbackCategory}
        for cat, cnt in rows:
            cat_val = cat.value if hasattr(cat, "value") else str(cat)
            counts[cat_val] = cnt
        return counts

    async def count_by_pillar(self, evaluation_id: uuid.UUID) -> dict[str, int]:
        """Calculate counts of feedback items grouped by scoring pillar.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Dictionary mapping pillar string values to integer counts.
        """
        stmt = (
            select(EvaluationFeedbackItem.pillar, func.count())
            .where(
                EvaluationFeedbackItem.evaluation_id == evaluation_id,
                EvaluationFeedbackItem.pillar.is_not(None),
            )
            .group_by(EvaluationFeedbackItem.pillar)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        counts: dict[str, int] = {p.value: 0 for p in ScoringPillar}
        for pil, cnt in rows:
            if pil is not None:
                pil_val = pil.value if hasattr(pil, "value") else str(pil)
                counts[pil_val] = cnt
        return counts

    async def get_feedback_summary_for_evaluation(
        self,
        evaluation_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Generate a complete categorical summary of feedback for an interview evaluation.

        Args:
            evaluation_id: Target InterviewEvaluation UUID.

        Returns:
            Dictionary containing category counts, total count, and pillar distribution.
        """
        category_counts = await self.count_by_category(evaluation_id)
        pillar_counts = await self.count_by_pillar(evaluation_id)
        total_items = sum(category_counts.values())

        return {
            "evaluation_id": evaluation_id,
            "total_items": total_items,
            "category_counts": category_counts,
            "pillar_counts": pillar_counts,
        }

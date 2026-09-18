"""System Design Interview Simulator - Evaluation Repository.

Provides specialized asynchronous data access operations for interview evaluations,
including scorecard upserts, pillar competency scoring, hiring recommendations, and user performance analytics.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import SeniorityLevel
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.evaluation import InterviewEvaluation
from app.models.session import InterviewSession
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class EvaluationRepository(BaseRepository[InterviewEvaluation]):
    """Repository handling scorecard persistence, hiring recommendations, and feedback for InterviewEvaluation."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize EvaluationRepository with active AsyncSession."""
        super().__init__(InterviewEvaluation, session)

    async def get_by_session_id(
        self,
        session_id: uuid.UUID,
        load_feedback: bool = True,
    ) -> InterviewEvaluation | None:
        """Retrieve evaluation scorecard for a specific interview session.

        Args:
            session_id: Interview session UUID.
            load_feedback: Whether to eagerly load feedback items.

        Returns:
            The InterviewEvaluation instance, or None if evaluation not yet produced.
        """
        stmt = select(InterviewEvaluation).where(InterviewEvaluation.session_id == session_id)
        if load_feedback:
            stmt = stmt.options(selectinload(InterviewEvaluation.feedback_items))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_session_id_or_raise(
        self,
        session_id: uuid.UUID,
        load_feedback: bool = True,
    ) -> InterviewEvaluation:
        """Retrieve evaluation scorecard or raise EntityNotFoundError.

        Args:
            session_id: Interview session UUID.
            load_feedback: Whether to eagerly load feedback items.

        Returns:
            The InterviewEvaluation instance.

        Raises:
            EntityNotFoundError: If evaluation does not exist for the session.
        """
        evaluation = await self.get_by_session_id(session_id, load_feedback=load_feedback)
        if evaluation is None:
            raise EntityNotFoundError(
                entity_name="InterviewEvaluation",
                entity_id=f"session_{session_id}",
            )
        return evaluation

    async def save_evaluation(
        self,
        session_id: uuid.UUID,
        overall_score: float,
        recommended_level: SeniorityLevel,
        hiring_recommendation: str,
        pillar_scores: dict[str, Any],
        summary: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> InterviewEvaluation:
        """Persist or update the evaluation scorecard for an interview session.

        Args:
            session_id: Interview session UUID.
            overall_score: Numerical score (e.g. 1.0 - 5.0).
            recommended_level: Evaluated technical level (MID, SENIOR, STAFF, PRINCIPAL).
            hiring_recommendation: Hiring verdict (STRONG_HIRE, HIRE, LEANING_HIRE, etc.).
            pillar_scores: Dictionary of score breakdowns per rubric pillar.
            summary: Comprehensive qualitative synthesis debrief.
            metadata_json: Optional evaluation context metadata.

        Returns:
            The created or updated InterviewEvaluation instance.
        """
        evaluation = await self.get_by_session_id(session_id, load_feedback=False)

        if evaluation is not None:
            evaluation.overall_score = overall_score
            evaluation.recommended_level = recommended_level
            evaluation.hiring_recommendation = hiring_recommendation.strip()
            evaluation.pillar_scores = pillar_scores
            evaluation.summary = summary.strip()
            if metadata_json:
                evaluation.metadata_json = metadata_json

            await self._session.flush()
            await self._session.refresh(evaluation)
            logger.info("Updated existing evaluation %s for session %s", evaluation.id, session_id)
            return evaluation

        new_evaluation = InterviewEvaluation(
            session_id=session_id,
            overall_score=overall_score,
            recommended_level=recommended_level,
            hiring_recommendation=hiring_recommendation.strip(),
            pillar_scores=pillar_scores,
            summary=summary.strip(),
            metadata_json=metadata_json or {},
        )
        created = await self.create(new_evaluation, flush=True)
        logger.info(
            "Created evaluation %s for session %s (score: %.2f, recommendation: %s)",
            created.id,
            session_id,
            overall_score,
            hiring_recommendation,
        )
        return created

    async def list_evaluations_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> Sequence[InterviewEvaluation]:
        """Query evaluation scorecards for all interviews conducted by a specific candidate.

        Args:
            user_id: Candidate user UUID.
            skip: Offset number.
            limit: Maximum scorecards to return.

        Returns:
            Sequence of InterviewEvaluation records ordered by created_at desc.
        """
        stmt = (
            select(InterviewEvaluation)
            .join(InterviewSession, InterviewEvaluation.session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.is_deleted.is_(False),
            )
            .order_by(InterviewEvaluation.created_at.desc())
            .offset(skip)
            .limit(limit)
            .options(selectinload(InterviewEvaluation.feedback_items))
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_average_score_for_user(self, user_id: uuid.UUID) -> float | None:
        """Calculate average interview score achieved by a candidate across all completed interviews.

        Args:
            user_id: Candidate user UUID.

        Returns:
            Average score float, or None if user has no completed evaluations.
        """
        stmt = (
            select(func.avg(InterviewEvaluation.overall_score))
            .join(InterviewSession, InterviewEvaluation.session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.is_deleted.is_(False),
            )
        )
        result = await self._session.execute(stmt)
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    async def count_evaluations(
        self,
        recommended_level: SeniorityLevel | None = None,
        hiring_recommendation: str | None = None,
    ) -> int:
        """Count total evaluations across the system with optional filters.

        Args:
            recommended_level: Optional SeniorityLevel filter.
            hiring_recommendation: Optional hiring decision filter.

        Returns:
            Total integer count.
        """
        stmt = select(func.count()).select_from(InterviewEvaluation)
        if recommended_level is not None:
            stmt = stmt.where(InterviewEvaluation.recommended_level == recommended_level)
        if hiring_recommendation is not None:
            stmt = stmt.where(
                func.lower(InterviewEvaluation.hiring_recommendation) == hiring_recommendation.strip().lower()
            )

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

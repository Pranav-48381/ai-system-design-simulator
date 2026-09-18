"""System Design Interview Simulator - Stage Progress Repository.

Provides specialized asynchronous data access operations for per-stage execution progress,
including stage lifecycle transitions, criteria tracking, state snapshots, and turn metrics.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewStage
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.stage_progress import SessionStageProgress
from app.repositories.base import BaseRepository

logger = get_logger(__name__)

ALL_INTERVIEW_STAGES = [
    InterviewStage.CLARIFICATION,
    InterviewStage.ESTIMATION,
    InterviewStage.ARCHITECTURE,
    InterviewStage.DEEP_DIVE,
    InterviewStage.BOTTLENECK,
    InterviewStage.EVALUATION,
]


class StageProgressRepository(BaseRepository[SessionStageProgress]):
    """Repository handling per-stage progress, timing metrics, and criteria satisfaction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize StageProgressRepository with active AsyncSession."""
        super().__init__(SessionStageProgress, session)

    async def get_by_session_and_stage(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
    ) -> SessionStageProgress | None:
        """Retrieve progress record for a specific session and architectural stage.

        Args:
            session_id: Interview session UUID.
            stage: Target InterviewStage.

        Returns:
            The SessionStageProgress instance or None if not initialized.
        """
        stmt = select(SessionStageProgress).where(
            SessionStageProgress.session_id == session_id,
            SessionStageProgress.stage == stage,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_session_and_stage_or_raise(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
    ) -> SessionStageProgress:
        """Retrieve stage progress record or raise EntityNotFoundError.

        Args:
            session_id: Interview session UUID.
            stage: Target InterviewStage.

        Returns:
            The SessionStageProgress instance.

        Raises:
            EntityNotFoundError: If stage progress record does not exist.
        """
        progress = await self.get_by_session_and_stage(session_id, stage)
        if progress is None:
            raise EntityNotFoundError(
                entity_name="SessionStageProgress",
                entity_id=f"session_{session_id}_stage_{stage.value}",
            )
        return progress

    async def list_by_session(
        self,
        session_id: uuid.UUID,
    ) -> Sequence[SessionStageProgress]:
        """Query all stage progress records for an interview session in chronological stage order.

        Args:
            session_id: Interview session UUID.

        Returns:
            Sequence of SessionStageProgress records.
        """
        stmt = (
            select(SessionStageProgress)
            .where(SessionStageProgress.session_id == session_id)
            .order_by(SessionStageProgress.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def initialize_stages_for_session(
        self,
        session_id: uuid.UUID,
    ) -> Sequence[SessionStageProgress]:
        """Initialize default progress tracking records for all 6 interview stages.

        Args:
            session_id: Target interview session UUID.

        Returns:
            Sequence of created SessionStageProgress records.
        """
        records: list[SessionStageProgress] = []
        for stage in ALL_INTERVIEW_STAGES:
            existing = await self.get_by_session_and_stage(session_id, stage)
            if existing is None:
                record = SessionStageProgress(
                    session_id=session_id,
                    stage=stage,
                    status="pending",
                    turns_spent=0,
                    duration_seconds=0,
                    criteria_met=[],
                    stage_state={},
                )
                self._session.add(record)
                records.append(record)

        if records:
            await self._session.flush()
            for r in records:
                await self._session.refresh(r)

        logger.info("Initialized %d stage progress records for session %s", len(records), session_id)
        return records

    async def start_stage(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
    ) -> SessionStageProgress:
        """Mark a stage as started ('in_progress') and record start timestamp.

        Args:
            session_id: Session UUID.
            stage: Target stage to begin.

        Returns:
            The updated SessionStageProgress instance.
        """
        progress = await self.get_by_session_and_stage(session_id, stage)
        if progress is None:
            progress = SessionStageProgress(
                session_id=session_id,
                stage=stage,
                status="in_progress",
                started_at=datetime.now(timezone.utc),
            )
            return await self.create(progress, flush=True)

        progress.status = "in_progress"
        if progress.started_at is None:
            progress.started_at = datetime.now(timezone.utc)

        await self._session.flush()
        await self._session.refresh(progress)
        logger.info("Stage %s marked in_progress for session %s", stage.value, session_id)
        return progress

    async def complete_stage(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        criteria_met: list[str] | None = None,
        notes: str | None = None,
        turns_spent: int | None = None,
        duration_seconds: int | None = None,
    ) -> SessionStageProgress:
        """Mark a stage as completed with criteria, notes, and duration accounting.

        Args:
            session_id: Session UUID.
            stage: Completed InterviewStage.
            criteria_met: Optional list of satisfied rubric criteria IDs.
            notes: Optional interviewer debrief notes.
            turns_spent: Optional turns expended in this stage.
            duration_seconds: Optional duration elapsed in seconds.

        Returns:
            The updated SessionStageProgress instance.
        """
        progress = await self.get_by_session_and_stage_or_raise(session_id, stage)
        now = datetime.now(timezone.utc)
        progress.status = "completed"
        progress.completed_at = now

        if criteria_met is not None:
            # Merge existing and newly met criteria without duplicates
            combined = list(set(progress.criteria_met + criteria_met))
            progress.criteria_met = combined

        if notes is not None:
            progress.notes = notes

        if turns_spent is not None:
            progress.turns_spent = turns_spent

        if duration_seconds is not None:
            progress.duration_seconds = duration_seconds
        elif progress.started_at is not None and progress.duration_seconds == 0:
            elapsed = int((now - progress.started_at).total_seconds())
            progress.duration_seconds = max(0, elapsed)

        await self._session.flush()
        await self._session.refresh(progress)
        logger.info("Stage %s completed for session %s (duration: %ds)", stage.value, session_id, progress.duration_seconds)
        return progress

    async def record_stage_turn(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        turns: int = 1,
        additional_seconds: int = 0,
    ) -> SessionStageProgress:
        """Increment turn and duration metrics for the active stage.

        Args:
            session_id: Session UUID.
            stage: Current InterviewStage.
            turns: Number of turns to add (default 1).
            additional_seconds: Additional elapsed seconds.

        Returns:
            The updated SessionStageProgress instance.
        """
        progress = await self.get_by_session_and_stage(session_id, stage)
        if progress is None:
            progress = await self.start_stage(session_id, stage)

        progress.turns_spent += turns
        if additional_seconds > 0:
            progress.duration_seconds += additional_seconds

        await self._session.flush()
        await self._session.refresh(progress)
        return progress

    async def add_criteria_met(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        criterion_id: str,
    ) -> SessionStageProgress:
        """Record an individual rubric criterion as satisfied.

        Args:
            session_id: Session UUID.
            stage: Active InterviewStage.
            criterion_id: Identifier of satisfied criterion.

        Returns:
            The updated SessionStageProgress instance.
        """
        progress = await self.get_by_session_and_stage_or_raise(session_id, stage)
        current = list(progress.criteria_met)
        if criterion_id not in current:
            current.append(criterion_id)
            progress.criteria_met = current
            await self._session.flush()
            await self._session.refresh(progress)

        return progress

    async def update_stage_state(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        state_patch: dict[str, Any],
    ) -> SessionStageProgress:
        """Update and merge arbitrary JSON stage state attributes.

        Args:
            session_id: Session UUID.
            stage: Active InterviewStage.
            state_patch: Dictionary of state keys to update.

        Returns:
            The updated SessionStageProgress instance.
        """
        progress = await self.get_by_session_and_stage_or_raise(session_id, stage)
        merged = dict(progress.stage_state)
        merged.update(state_patch)
        progress.stage_state = merged
        await self._session.flush()
        await self._session.refresh(progress)
        return progress

    async def get_total_duration_seconds(self, session_id: uuid.UUID) -> int:
        """Calculate total cumulative seconds spent across all stages.

        Args:
            session_id: Session UUID.

        Returns:
            Total elapsed seconds.
        """
        stmt = select(
            func.coalesce(func.sum(SessionStageProgress.duration_seconds), 0)
        ).where(SessionStageProgress.session_id == session_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

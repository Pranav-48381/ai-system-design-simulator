"""System Design Interview Simulator - Session Repository.

Provides specialized asynchronous data access operations for interview sessions,
including active session tracking, stage progression, turn increments, and lifecycle state management.
"""

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    InterviewerPersona,
    InterviewStage,
    SeniorityLevel,
    SessionStatus,
)
from app.core.exceptions import EntityNotFoundError, InvalidStateTransitionError
from app.core.logging import get_logger
from app.models.session import InterviewSession
from app.repositories.base import BaseRepository

logger = get_logger(__name__)

ACTIVE_SESSION_STATUSES = {
    SessionStatus.PENDING,
    SessionStatus.IN_PROGRESS,
    SessionStatus.PAUSED,
}


class SessionRepository(BaseRepository[InterviewSession]):
    """Repository handling persistence, active state, and stage progression for InterviewSession."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize SessionRepository with active AsyncSession."""
        super().__init__(InterviewSession, session)

    async def get_by_id_with_details(
        self,
        session_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> InterviewSession | None:
        """Retrieve an interview session with problem, user, and rubric eagerly loaded.

        Args:
            session_id: UUID of the session.
            include_deleted: Whether to include soft-deleted sessions.

        Returns:
            The InterviewSession instance with related entities, or None.
        """
        stmt = (
            select(InterviewSession)
            .where(InterviewSession.id == session_id)
            .options(
                selectinload(InterviewSession.problem),
                selectinload(InterviewSession.user),
                selectinload(InterviewSession.rubric),
            )
        )
        if not include_deleted:
            stmt = stmt.where(InterviewSession.is_deleted.is_(False))

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_id_with_details_or_raise(
        self,
        session_id: uuid.UUID,
        include_deleted: bool = False,
    ) -> InterviewSession:
        """Retrieve an interview session with details or raise EntityNotFoundError.

        Args:
            session_id: UUID of the session.
            include_deleted: Whether to include soft-deleted sessions.

        Returns:
            The persisted InterviewSession instance.

        Raises:
            EntityNotFoundError: If session not found.
        """
        session_obj = await self.get_by_id_with_details(session_id, include_deleted=include_deleted)
        if session_obj is None:
            raise EntityNotFoundError(entity_name="InterviewSession", entity_id=session_id)
        return session_obj

    async def get_active_session(
        self,
        user_id: uuid.UUID,
        load_details: bool = True,
    ) -> InterviewSession | None:
        """Retrieve the currently active interview session for a candidate.

        An active session is defined as one with status PENDING, IN_PROGRESS, or PAUSED,
        which has not been soft-deleted.

        Args:
            user_id: Candidate user UUID.
            load_details: Whether to eagerly load problem and user.

        Returns:
            The most recent active InterviewSession instance, or None.
        """
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.status.in_(ACTIVE_SESSION_STATUSES),
                InterviewSession.is_deleted.is_(False),
            )
            .order_by(InterviewSession.created_at.desc())
            .limit(1)
        )
        if load_details:
            stmt = stmt.options(
                selectinload(InterviewSession.problem),
                selectinload(InterviewSession.user),
            )

        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_session_or_raise(
        self,
        user_id: uuid.UUID,
        load_details: bool = True,
    ) -> InterviewSession:
        """Retrieve the candidate's active session or raise EntityNotFoundError.

        Args:
            user_id: Candidate user UUID.
            load_details: Whether to eagerly load related entities.

        Returns:
            The active InterviewSession instance.

        Raises:
            EntityNotFoundError: If no active session is found for the user.
        """
        session_obj = await self.get_active_session(user_id, load_details=load_details)
        if session_obj is None:
            raise EntityNotFoundError(
                entity_name="InterviewSession",
                entity_id=f"active_session_for_user_{user_id}",
            )
        return session_obj

    async def list_by_user(
        self,
        user_id: uuid.UUID,
        status: SessionStatus | None = None,
        skip: int = 0,
        limit: int = 20,
        load_problem: bool = True,
    ) -> Sequence[InterviewSession]:
        """Query sessions for a candidate with optional status filter and pagination.

        Args:
            user_id: Candidate UUID.
            status: Optional SessionStatus filter.
            skip: Offset number.
            limit: Maximum items to return.
            load_problem: Whether to eagerly load the associated problem.

        Returns:
            Sequence of InterviewSession records.
        """
        stmt = (
            select(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.is_deleted.is_(False),
            )
            .order_by(InterviewSession.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if status is not None:
            stmt = stmt.where(InterviewSession.status == status)
        if load_problem:
            stmt = stmt.options(selectinload(InterviewSession.problem))

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_user(
        self,
        user_id: uuid.UUID,
        status: SessionStatus | None = None,
    ) -> int:
        """Count total sessions for a candidate with optional status filter.

        Args:
            user_id: Candidate UUID.
            status: Optional status filter.

        Returns:
            Total integer count.
        """
        stmt = (
            select(func.count())
            .select_from(InterviewSession)
            .where(
                InterviewSession.user_id == user_id,
                InterviewSession.is_deleted.is_(False),
            )
        )
        if status is not None:
            stmt = stmt.where(InterviewSession.status == status)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def create_session(
        self,
        user_id: uuid.UUID,
        problem_id: uuid.UUID,
        rubric_id: uuid.UUID | None = None,
        persona: InterviewerPersona = InterviewerPersona.COLLABORATIVE,
        target_level: SeniorityLevel = SeniorityLevel.SENIOR,
        initial_stage: InterviewStage = InterviewStage.CLARIFICATION,
        metadata_json: dict[str, Any] | None = None,
    ) -> InterviewSession:
        """Create and persist a new interview session instance.

        Args:
            user_id: Candidate user UUID.
            problem_id: Problem specification UUID.
            rubric_id: Optional scoring rubric UUID.
            persona: Interviewer persona personality archetype.
            target_level: Candidate target seniority tier.
            initial_stage: Starting interview stage.
            metadata_json: Optional initial session metadata.

        Returns:
            The created and persisted InterviewSession instance.
        """
        session_obj = InterviewSession(
            user_id=user_id,
            problem_id=problem_id,
            rubric_id=rubric_id,
            persona=persona,
            target_level=target_level,
            current_stage=initial_stage,
            status=SessionStatus.PENDING,
            total_turns=0,
            total_duration_seconds=0,
            metadata_json=metadata_json or {},
        )
        created_session = await self.create(session_obj, flush=True)
        logger.info("Created interview session %s for user %s", created_session.id, user_id)
        return created_session

    async def start_session(self, session_id: uuid.UUID) -> InterviewSession:
        """Transition an interview session to IN_PROGRESS and record start timestamp.

        Args:
            session_id: Session UUID.

        Returns:
            The updated InterviewSession instance.

        Raises:
            InvalidStateTransitionError: If session is already completed or abandoned.
        """
        session_obj = await self.get_or_raise(session_id)
        if session_obj.status in {SessionStatus.COMPLETED, SessionStatus.ABANDONED}:
            raise InvalidStateTransitionError(
                current_state=session_obj.status.value,
                target_state=SessionStatus.IN_PROGRESS.value,
            )

        now = datetime.now(timezone.utc)
        if session_obj.started_at is None:
            session_obj.started_at = now

        session_obj.status = SessionStatus.IN_PROGRESS
        await self._session.flush()
        await self._session.refresh(session_obj)
        logger.info("Started interview session %s", session_id)
        return session_obj

    async def pause_session(self, session_id: uuid.UUID) -> InterviewSession:
        """Transition an active session to PAUSED status.

        Args:
            session_id: Session UUID.

        Returns:
            The updated InterviewSession instance.

        Raises:
            InvalidStateTransitionError: If session is not IN_PROGRESS.
        """
        session_obj = await self.get_or_raise(session_id)
        if session_obj.status != SessionStatus.IN_PROGRESS:
            raise InvalidStateTransitionError(
                current_state=session_obj.status.value,
                target_state=SessionStatus.PAUSED.value,
            )

        session_obj.status = SessionStatus.PAUSED
        await self._session.flush()
        await self._session.refresh(session_obj)
        logger.info("Paused interview session %s", session_id)
        return session_obj

    async def resume_session(self, session_id: uuid.UUID) -> InterviewSession:
        """Resume a PAUSED interview session back to IN_PROGRESS.

        Args:
            session_id: Session UUID.

        Returns:
            The resumed InterviewSession instance.

        Raises:
            InvalidStateTransitionError: If session is not PAUSED.
        """
        session_obj = await self.get_or_raise(session_id)
        if session_obj.status != SessionStatus.PAUSED:
            raise InvalidStateTransitionError(
                current_state=session_obj.status.value,
                target_state=SessionStatus.IN_PROGRESS.value,
            )

        session_obj.status = SessionStatus.IN_PROGRESS
        await self._session.flush()
        await self._session.refresh(session_obj)
        logger.info("Resumed interview session %s", session_id)
        return session_obj

    async def advance_stage(
        self,
        session_id: uuid.UUID,
        next_stage: InterviewStage,
    ) -> InterviewSession:
        """Advance the interview session to the next architectural stage.

        Args:
            session_id: Session UUID.
            next_stage: Target InterviewStage to enter.

        Returns:
            The updated InterviewSession instance.
        """
        session_obj = await self.get_or_raise(session_id)
        logger.info(
            "Advancing session %s stage: %s -> %s",
            session_id,
            session_obj.current_stage.value,
            next_stage.value,
        )
        session_obj.current_stage = next_stage
        await self._session.flush()
        await self._session.refresh(session_obj)
        return session_obj

    async def increment_turns(
        self,
        session_id: uuid.UUID,
        turns: int = 1,
        additional_duration_seconds: int = 0,
    ) -> InterviewSession:
        """Increment dialogue turn counter and update elapsed time.

        Args:
            session_id: Session UUID.
            turns: Number of dialogue turns to add (default 1).
            additional_duration_seconds: Additional elapsed seconds to accumulate.

        Returns:
            The updated InterviewSession instance.
        """
        session_obj = await self.get_or_raise(session_id)
        session_obj.total_turns += turns
        if additional_duration_seconds > 0:
            session_obj.total_duration_seconds += additional_duration_seconds

        await self._session.flush()
        await self._session.refresh(session_obj)
        return session_obj

    async def finish_session(
        self,
        session_id: uuid.UUID,
        status: SessionStatus = SessionStatus.COMPLETED,
    ) -> InterviewSession:
        """Mark an interview session as finished (COMPLETED or ABANDONED).

        Args:
            session_id: Session UUID.
            status: Final status (COMPLETED or ABANDONED).

        Returns:
            The finished InterviewSession instance.
        """
        session_obj = await self.get_or_raise(session_id)
        now = datetime.now(timezone.utc)
        session_obj.ended_at = now
        session_obj.status = status

        if session_obj.started_at is not None and session_obj.total_duration_seconds == 0:
            elapsed = int((now - session_obj.started_at).total_seconds())
            session_obj.total_duration_seconds = max(0, elapsed)

        await self._session.flush()
        await self._session.refresh(session_obj)
        logger.info("Finished interview session %s with status %s", session_id, status.value)
        return session_obj

    async def soft_delete(self, session_id: uuid.UUID) -> bool:
        """Soft delete an interview session by setting is_deleted=True.

        Args:
            session_id: UUID of session to delete.

        Returns:
            True if soft-deleted, False if not found.
        """
        session_obj = await self.get_by_id(session_id)
        if session_obj is None or session_obj.is_deleted:
            return False

        session_obj.is_deleted = True
        session_obj.deleted_at = datetime.now(timezone.utc)
        await self._session.flush()
        logger.info("InterviewSession %s soft-deleted successfully", session_id)
        return True

    async def restore(self, session_id: uuid.UUID) -> bool:
        """Restore a previously soft-deleted interview session.

        Args:
            session_id: UUID of session to restore.

        Returns:
            True if restored, False if not found or not deleted.
        """
        stmt = select(InterviewSession).where(
            InterviewSession.id == session_id,
            InterviewSession.is_deleted.is_(True),
        )
        result = await self._session.execute(stmt)
        session_obj = result.scalar_one_or_none()
        if session_obj is None:
            return False

        session_obj.is_deleted = False
        session_obj.deleted_at = None
        await self._session.flush()
        logger.info("InterviewSession %s restored successfully", session_id)
        return True

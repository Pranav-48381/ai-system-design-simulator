"""System Design Interview Simulator - Message Repository.

Provides specialized asynchronous data access operations for interview conversation messages,
including sequential turn ordering, stage-specific message history, token accounting, and latency aggregation.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewStage, SpeakerRole
from app.core.logging import get_logger
from app.models.message import InterviewMessage
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class MessageRepository(BaseRepository[InterviewMessage]):
    """Repository handling dialogue turn persistence and sequence management for InterviewMessage."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize MessageRepository with active AsyncSession."""
        super().__init__(InterviewMessage, session)

    async def get_next_sequence_number(self, session_id: uuid.UUID) -> int:
        """Calculate the next chronological sequence number for a session.

        Args:
            session_id: Interview session UUID.

        Returns:
            The next sequence integer (1-indexed).
        """
        stmt = select(
            func.coalesce(func.max(InterviewMessage.sequence_number), 0) + 1
        ).where(InterviewMessage.session_id == session_id)
        result = await self._session.execute(stmt)
        return result.scalar_one()

    async def create_message(
        self,
        session_id: uuid.UUID,
        role: SpeakerRole,
        stage: InterviewStage,
        content: str,
        sequence_number: int | None = None,
        token_count: int | None = None,
        latency_ms: float | None = None,
        metadata_json: dict[str, Any] | None = None,
    ) -> InterviewMessage:
        """Create and persist a new dialogue turn message.

        If sequence_number is omitted, automatically computes the next sequential index.

        Args:
            session_id: Target interview session UUID.
            role: Speaker role (CANDIDATE, INTERVIEWER, SYSTEM).
            stage: Current architectural interview stage.
            content: Text dialogue utterance.
            sequence_number: Optional explicit sequence index.
            token_count: Optional recorded token count.
            latency_ms: Optional generation/processing latency in milliseconds.
            metadata_json: Optional contextual metadata dict.

        Returns:
            The persisted InterviewMessage instance.
        """
        if sequence_number is None:
            sequence_number = await self.get_next_sequence_number(session_id)

        message = InterviewMessage(
            session_id=session_id,
            sequence_number=sequence_number,
            role=role,
            stage=stage,
            content=content.strip(),
            token_count=token_count,
            latency_ms=latency_ms,
            metadata_json=metadata_json or {},
        )
        created_message = await self.create(message, flush=True)
        logger.debug(
            "Persisted message %s (session: %s, seq: %d, role: %s)",
            created_message.id,
            session_id,
            sequence_number,
            role.value,
        )
        return created_message

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage | None = None,
        role: SpeakerRole | None = None,
        skip: int = 0,
        limit: int = 100,
        ascending: bool = True,
    ) -> Sequence[InterviewMessage]:
        """Query chronological dialogue messages for a session.

        Args:
            session_id: Interview session UUID.
            stage: Optional stage filter.
            role: Optional speaker role filter.
            skip: Offset number.
            limit: Maximum messages to return.
            ascending: Sort ascending by sequence_number if True, descending if False.

        Returns:
            Sequence of InterviewMessage records.
        """
        order_clause = (
            InterviewMessage.sequence_number.asc()
            if ascending
            else InterviewMessage.sequence_number.desc()
        )
        stmt = (
            select(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .order_by(order_clause)
            .offset(skip)
            .limit(limit)
        )
        if stage is not None:
            stmt = stmt.where(InterviewMessage.stage == stage)
        if role is not None:
            stmt = stmt.where(InterviewMessage.role == role)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_recent_messages(
        self,
        session_id: uuid.UUID,
        limit: int = 20,
    ) -> Sequence[InterviewMessage]:
        """Fetch the most recent N messages for LLM context window hydration.

        Results are returned in ascending chronological order.

        Args:
            session_id: Session UUID.
            limit: Number of recent messages to retrieve.

        Returns:
            Chronologically ordered sequence of the most recent messages.
        """
        stmt = (
            select(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .order_by(InterviewMessage.sequence_number.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        recent_desc = result.scalars().all()
        # Return in ascending chronological order for prompt injection
        return list(reversed(recent_desc))

    async def get_stage_messages(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
    ) -> Sequence[InterviewMessage]:
        """Query all messages exchanged during a specific interview stage.

        Args:
            session_id: Session UUID.
            stage: Target InterviewStage.

        Returns:
            Sequence of messages ordered by sequence_number ascending.
        """
        stmt = (
            select(InterviewMessage)
            .where(
                InterviewMessage.session_id == session_id,
                InterviewMessage.stage == stage,
            )
            .order_by(InterviewMessage.sequence_number.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_session(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage | None = None,
        role: SpeakerRole | None = None,
    ) -> int:
        """Count total messages matching criteria for a session.

        Args:
            session_id: Session UUID.
            stage: Optional stage filter.
            role: Optional role filter.

        Returns:
            Total integer count.
        """
        stmt = (
            select(func.count())
            .select_from(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
        )
        if stage is not None:
            stmt = stmt.where(InterviewMessage.stage == stage)
        if role is not None:
            stmt = stmt.where(InterviewMessage.role == role)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_total_token_count(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage | None = None,
    ) -> int:
        """Calculate total tokens consumed across dialogue turns for a session.

        Args:
            session_id: Session UUID.
            stage: Optional stage filter.

        Returns:
            Total token count integer.
        """
        stmt = select(func.coalesce(func.sum(InterviewMessage.token_count), 0)).where(
            InterviewMessage.session_id == session_id,
        )
        if stage is not None:
            stmt = stmt.where(InterviewMessage.stage == stage)

        result = await self._session.execute(stmt)
        return int(result.scalar_one() or 0)

    async def get_average_latency_ms(
        self,
        session_id: uuid.UUID,
        role: SpeakerRole = SpeakerRole.INTERVIEWER,
    ) -> float | None:
        """Calculate average latency in milliseconds for a specific role.

        Args:
            session_id: Session UUID.
            role: Target speaker role (defaults to INTERVIEWER).

        Returns:
            Average latency float in milliseconds, or None if no latencies recorded.
        """
        stmt = select(func.avg(InterviewMessage.latency_ms)).where(
            InterviewMessage.session_id == session_id,
            InterviewMessage.role == role,
            InterviewMessage.latency_ms.isnot(None),
        )
        result = await self._session.execute(stmt)
        avg = result.scalar_one_or_none()
        return float(avg) if avg is not None else None

    async def delete_by_session(self, session_id: uuid.UUID) -> int:
        """Delete all messages associated with an interview session.

        Args:
            session_id: Session UUID.

        Returns:
            Count of deleted messages.
        """
        stmt = (
            sql_delete(InterviewMessage)
            .where(InterviewMessage.session_id == session_id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        deleted_count = result.rowcount or 0
        logger.info("Deleted %d messages for session %s", deleted_count, session_id)
        return deleted_count

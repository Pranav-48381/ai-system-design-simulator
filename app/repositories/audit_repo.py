"""System Design Interview Simulator - Audit Repository.

Provides specialized asynchronous data access operations for interview audit logs,
including immutable event appending, timeline reconstruction, event type frequency analysis,
hint utilization tracking, and canvas modification counting.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewStage
from app.core.logging import get_logger
from app.models.audit_log import SessionAuditLog
from app.models.enums import AuditEventType
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class AuditRepository(BaseRepository[SessionAuditLog]):
    """Repository handling immutable audit logging and session timeline reconstruction."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize AuditRepository with active AsyncSession."""
        super().__init__(SessionAuditLog, session)

    async def record_event(
        self,
        session_id: uuid.UUID,
        event_type: AuditEventType,
        stage: InterviewStage | None = None,
        action: str | None = None,
        payload: dict[str, Any] | None = None,
        flush: bool = True,
    ) -> SessionAuditLog:
        """Append an immutable audit log entry for an interview session event.

        Args:
            session_id: Target InterviewSession UUID.
            event_type: Classification of the audit event.
            stage: Architectural stage at the moment of event occurrence.
            action: Human-readable action moniker or slash-command.
            payload: Contextual JSON payload containing event parameters.
            flush: Whether to execute session flush immediately.

        Returns:
            The created SessionAuditLog record.
        """
        audit_entry = SessionAuditLog(
            session_id=session_id,
            event_type=event_type,
            stage=stage,
            action=action.strip() if action else None,
            payload=payload or {},
        )
        created = await self.create(audit_entry, flush=flush)
        logger.debug(
            "Audit event logged: session=%s event=%s stage=%s action=%s",
            session_id,
            event_type.value,
            stage.value if stage else None,
            action,
        )
        return created

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        event_type: AuditEventType | None = None,
        stage: InterviewStage | None = None,
        skip: int = 0,
        limit: int = 100,
        ascending: bool = True,
    ) -> Sequence[SessionAuditLog]:
        """Query audit log records for an interview session with optional filters.

        Args:
            session_id: Target InterviewSession UUID.
            event_type: Optional AuditEventType filter.
            stage: Optional InterviewStage filter.
            skip: Number of records to skip (offset).
            limit: Maximum records to return.
            ascending: Sort order by created_at (default True for chronological replay).

        Returns:
            Sequence of SessionAuditLog records matching criteria.
        """
        stmt = select(SessionAuditLog).where(SessionAuditLog.session_id == session_id)

        if event_type is not None:
            stmt = stmt.where(SessionAuditLog.event_type == event_type)
        if stage is not None:
            stmt = stmt.where(SessionAuditLog.stage == stage)

        if ascending:
            stmt = stmt.order_by(SessionAuditLog.created_at.asc())
        else:
            stmt = stmt.order_by(SessionAuditLog.created_at.desc())

        stmt = stmt.offset(skip).limit(limit)
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_latest_event(
        self,
        session_id: uuid.UUID,
        event_type: AuditEventType | None = None,
    ) -> SessionAuditLog | None:
        """Retrieve the most recent audit event for a session.

        Args:
            session_id: Target InterviewSession UUID.
            event_type: Optional event type filter.

        Returns:
            The most recent SessionAuditLog or None.
        """
        stmt = (
            select(SessionAuditLog)
            .where(SessionAuditLog.session_id == session_id)
        )
        if event_type is not None:
            stmt = stmt.where(SessionAuditLog.event_type == event_type)

        stmt = stmt.order_by(SessionAuditLog.created_at.desc()).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_events_by_type(self, session_id: uuid.UUID) -> dict[str, int]:
        """Count audit occurrences grouped by event type for a session.

        Args:
            session_id: Target InterviewSession UUID.

        Returns:
            Dictionary mapping event type values to integer counts.
        """
        stmt = (
            select(SessionAuditLog.event_type, func.count())
            .where(SessionAuditLog.session_id == session_id)
            .group_by(SessionAuditLog.event_type)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        counts: dict[str, int] = {e.value: 0 for e in AuditEventType}
        for event_type, cnt in rows:
            et_val = event_type.value if hasattr(event_type, "value") else str(event_type)
            counts[et_val] = cnt
        return counts

    async def count_hints_used(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage | None = None,
    ) -> int:
        """Calculate total hints requested by candidate during the interview or a stage.

        Args:
            session_id: Target InterviewSession UUID.
            stage: Optional stage to constrain count.

        Returns:
            Total integer count of HINT_REQUESTED events.
        """
        stmt = (
            select(func.count())
            .select_from(SessionAuditLog)
            .where(
                SessionAuditLog.session_id == session_id,
                SessionAuditLog.event_type == AuditEventType.HINT_REQUESTED,
            )
        )
        if stage is not None:
            stmt = stmt.where(SessionAuditLog.stage == stage)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def count_canvas_modifications(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage | None = None,
    ) -> int:
        """Calculate total diagram and whiteboard edits performed during the session.

        Args:
            session_id: Target InterviewSession UUID.
            stage: Optional stage to constrain count.

        Returns:
            Total integer count of CANVAS_MODIFIED events.
        """
        stmt = (
            select(func.count())
            .select_from(SessionAuditLog)
            .where(
                SessionAuditLog.session_id == session_id,
                SessionAuditLog.event_type == AuditEventType.CANVAS_MODIFIED,
            )
        )
        if stage is not None:
            stmt = stmt.where(SessionAuditLog.stage == stage)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def get_session_timeline(
        self,
        session_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Construct a structured, chronological timeline representation of the interview.

        Args:
            session_id: Target InterviewSession UUID.

        Returns:
            List of timeline event dictionaries suitable for UI display and debrief generation.
        """
        events = await self.list_by_session(session_id=session_id, limit=500, ascending=True)
        timeline: list[dict[str, Any]] = []

        for ev in events:
            timeline.append({
                "id": ev.id,
                "timestamp": ev.created_at.isoformat() if ev.created_at else None,
                "event_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
                "stage": ev.stage.value if ev.stage and hasattr(ev.stage, "value") else str(ev.stage) if ev.stage else None,
                "action": ev.action,
                "payload_summary": {k: v for k, v in ev.payload.items() if k not in ("token", "secret")} if ev.payload else {},
            })

        return timeline

    async def bulk_record_events(
        self,
        session_id: uuid.UUID,
        events: Sequence[dict[str, Any]],
        flush: bool = True,
    ) -> Sequence[SessionAuditLog]:
        """Persist multiple audit events in a batch operation.

        Args:
            session_id: Target InterviewSession UUID.
            events: Sequence of event dictionaries (event_type, stage, action, payload).
            flush: Whether to execute session flush immediately.

        Returns:
            The sequence of persisted SessionAuditLog records.
        """
        instances: list[SessionAuditLog] = []
        for raw in events:
            instances.append(
                SessionAuditLog(
                    session_id=session_id,
                    event_type=raw["event_type"],
                    stage=raw.get("stage"),
                    action=raw.get("action"),
                    payload=raw.get("payload", {}),
                )
            )

        persisted = await self.create_many(instances, flush=flush)
        logger.info(
            "Batch-recorded %d audit events for session %s",
            len(persisted),
            session_id,
        )
        return persisted

    async def delete_by_session(
        self,
        session_id: uuid.UUID,
        flush: bool = True,
    ) -> int:
        """Purge all audit logs associated with an interview session.

        Args:
            session_id: Target InterviewSession UUID.
            flush: Whether to execute session flush immediately.

        Returns:
            Total deleted records count.
        """
        stmt = sql_delete(SessionAuditLog).where(SessionAuditLog.session_id == session_id)
        result = await self._session.execute(stmt)
        if flush:
            await self._session.flush()

        deleted = result.rowcount or 0
        logger.info("Deleted %d audit logs for session %s", deleted, session_id)
        return deleted

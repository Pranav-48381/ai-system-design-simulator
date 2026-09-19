"""System Design Interview Simulator - Stage Metric Repository.

Provides specialized asynchronous data access operations for stage-level telemetry,
including token usage accounting, latency tracking, stage pacing analytics,
session aggregations, and global benchmark comparisons.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InterviewStage
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.stage_metric import StageMetric
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class StageMetricRepository(BaseRepository[StageMetric]):
    """Repository handling stage-level telemetry, token expenditure, and latency analytics."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize StageMetricRepository with active AsyncSession."""
        super().__init__(StageMetric, session)

    async def get_by_session_and_stage(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
    ) -> StageMetric | None:
        """Retrieve metrics record for a specific interview session and stage.

        Args:
            session_id: Interview session UUID.
            stage: Target InterviewStage.

        Returns:
            The StageMetric instance or None if not recorded yet.
        """
        stmt = select(StageMetric).where(
            StageMetric.session_id == session_id,
            StageMetric.stage == stage,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        flush: bool = True,
    ) -> StageMetric:
        """Retrieve existing stage metric or create a new initialized record.

        Args:
            session_id: Interview session UUID.
            stage: Target InterviewStage.
            flush: Whether to execute session flush immediately.

        Returns:
            The existing or newly created StageMetric instance.
        """
        metric = await self.get_by_session_and_stage(session_id, stage)
        if metric is not None:
            return metric

        new_metric = StageMetric(
            session_id=session_id,
            stage=stage,
            turn_count=0,
            duration_seconds=0.0,
            token_count_in=0,
            token_count_out=0,
            average_latency_ms=None,
            metadata_json={},
        )
        created = await self.create(new_metric, flush=flush)
        logger.debug("Initialized StageMetric for session %s, stage %s", session_id, stage.value)
        return created

    async def list_by_session(
        self,
        session_id: uuid.UUID,
    ) -> Sequence[StageMetric]:
        """Retrieve all stage metrics recorded for a specific interview session.

        Args:
            session_id: Interview session UUID.

        Returns:
            Sequence of StageMetric records ordered by created_at.
        """
        stmt = (
            select(StageMetric)
            .where(StageMetric.session_id == session_id)
            .order_by(StageMetric.created_at.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def record_stage_telemetry(
        self,
        session_id: uuid.UUID,
        stage: InterviewStage,
        turn_increment: int = 0,
        duration_seconds: float = 0.0,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: float | None = None,
        metadata_update: dict[str, Any] | None = None,
        flush: bool = True,
    ) -> StageMetric:
        """Accumulate telemetry data into a stage metric record.

        Args:
            session_id: Interview session UUID.
            stage: Target InterviewStage.
            turn_increment: Additional dialogue turns to add.
            duration_seconds: Additional elapsed seconds to add.
            tokens_in: Additional prompt tokens consumed.
            tokens_out: Additional completion tokens generated.
            latency_ms: Turn latency observation to incorporate into moving average.
            metadata_update: Optional additional metadata fields to merge.
            flush: Whether to execute session flush immediately.

        Returns:
            The updated StageMetric instance.
        """
        metric = await self.get_or_create(session_id, stage, flush=False)

        metric.turn_count += max(0, turn_increment)
        metric.duration_seconds += max(0.0, duration_seconds)
        metric.token_count_in += max(0, tokens_in)
        metric.token_count_out += max(0, tokens_out)

        if latency_ms is not None and latency_ms > 0:
            if metric.average_latency_ms is None:
                metric.average_latency_ms = latency_ms
            else:
                # Cumulative moving average weighted by turns
                prev_turns = max(1, metric.turn_count - turn_increment)
                metric.average_latency_ms = (
                    (metric.average_latency_ms * prev_turns) + latency_ms
                ) / metric.turn_count

        if metadata_update:
            current_meta = dict(metric.metadata_json or {})
            current_meta.update(metadata_update)
            metric.metadata_json = current_meta

        if flush:
            await self._session.flush()
            await self._session.refresh(metric)

        logger.debug(
            "Updated stage telemetry for session %s, stage %s: turns=%d, tokens_in=%d, tokens_out=%d",
            session_id,
            stage.value,
            metric.turn_count,
            metric.token_count_in,
            metric.token_count_out,
        )
        return metric

    async def get_session_aggregate_telemetry(
        self,
        session_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Calculate aggregated telemetry metrics across all stages for a session.

        Args:
            session_id: Target InterviewSession UUID.

        Returns:
            Dictionary containing total turns, total duration, token breakdown, and average latency.
        """
        stmt = (
            select(
                func.coalesce(func.sum(StageMetric.turn_count), 0),
                func.coalesce(func.sum(StageMetric.duration_seconds), 0.0),
                func.coalesce(func.sum(StageMetric.token_count_in), 0),
                func.coalesce(func.sum(StageMetric.token_count_out), 0),
                func.avg(StageMetric.average_latency_ms),
            )
            .where(StageMetric.session_id == session_id)
        )
        result = await self._session.execute(stmt)
        total_turns, total_duration, tokens_in, tokens_out, avg_lat = result.one()

        total_tokens = int(tokens_in) + int(tokens_out)
        return {
            "session_id": session_id,
            "total_turns": int(total_turns),
            "total_duration_seconds": float(total_duration),
            "total_duration_minutes": round(float(total_duration) / 60.0, 2),
            "token_count_in": int(tokens_in),
            "token_count_out": int(tokens_out),
            "total_token_count": total_tokens,
            "average_latency_ms": round(float(avg_lat), 2) if avg_lat is not None else None,
        }

    async def get_global_stage_benchmarks(self) -> dict[str, dict[str, float]]:
        """Compute aggregate system-wide benchmarks for each interview stage.

        Returns:
            Dictionary mapping stage names to average duration, turn count, and token usage.
        """
        stmt = (
            select(
                StageMetric.stage,
                func.avg(StageMetric.duration_seconds),
                func.avg(StageMetric.turn_count),
                func.avg(StageMetric.token_count_in + StageMetric.token_count_out),
                func.avg(StageMetric.average_latency_ms),
            )
            .group_by(StageMetric.stage)
        )
        result = await self._session.execute(stmt)
        rows = result.all()

        benchmarks: dict[str, dict[str, float]] = {}
        for stage, avg_dur, avg_turns, avg_tokens, avg_lat in rows:
            stage_key = stage.value if hasattr(stage, "value") else str(stage)
            benchmarks[stage_key] = {
                "avg_duration_seconds": round(float(avg_dur or 0.0), 2),
                "avg_turns": round(float(avg_turns or 0.0), 1),
                "avg_total_tokens": round(float(avg_tokens or 0.0), 1),
                "avg_latency_ms": round(float(avg_lat or 0.0), 2) if avg_lat is not None else 0.0,
            }

        return benchmarks

    async def delete_by_session(
        self,
        session_id: uuid.UUID,
        flush: bool = True,
    ) -> int:
        """Purge all stage metrics for an interview session.

        Args:
            session_id: Target InterviewSession UUID.
            flush: Whether to execute session flush immediately.

        Returns:
            Number of deleted metric records.
        """
        stmt = sql_delete(StageMetric).where(StageMetric.session_id == session_id)
        result = await self._session.execute(stmt)
        if flush:
            await self._session.flush()

        deleted = result.rowcount or 0
        logger.info("Deleted %d stage metrics for session %s", deleted, session_id)
        return deleted

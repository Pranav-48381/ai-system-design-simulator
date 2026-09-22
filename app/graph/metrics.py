"""System Design Interview Simulator - LangGraph Metrics Collector.

Provides real-time execution timing, LLM token consumption tracking, latency analytics,
and aggregation utilities for StateGraph nodes and interview stages. Collects fine-grained
telemetry that maps directly to persistent StageMetric models and performance reporting.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import math
import time
from typing import Any, AsyncIterator
from uuid import UUID

from app.core.constants import InterviewStage
from app.graph.types import NodeResult, TokenUsage

logger = logging.getLogger(__name__)


@dataclass
class NodeExecutionMetric:
    """Telemetry captured for a single LangGraph node invocation."""

    node_name: str
    stage: InterviewStage
    start_time: float
    end_time: float
    duration_ms: float
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    model_name: str | None = None
    is_success: bool = True
    error_message: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_name": self.node_name,
            "stage": self.stage.value,
            "duration_ms": round(self.duration_ms, 2),
            "token_usage": self.token_usage.to_dict(),
            "model_name": self.model_name,
            "is_success": self.is_success,
            "error_message": self.error_message,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class StageMetricsSummary:
    """Aggregated metrics and token economics for a specific interview stage."""

    stage: InterviewStage
    turn_count: int = 0
    duration_seconds: float = 0.0
    token_count_in: int = 0
    token_count_out: int = 0
    total_tokens: int = 0
    node_executions_count: int = 0
    average_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    error_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_db_dict(self, session_id: UUID | str) -> dict[str, Any]:
        """Convert summary into dictionary matching StageMetric database model attributes."""
        sess_uuid = UUID(str(session_id)) if isinstance(session_id, str) else session_id
        return {
            "session_id": sess_uuid,
            "stage": self.stage,
            "turn_count": self.turn_count,
            "duration_seconds": round(self.duration_seconds, 2),
            "token_count_in": self.token_count_in,
            "token_count_out": self.token_count_out,
            "average_latency_ms": round(self.average_latency_ms, 2),
            "metadata_json": {
                **self.metadata,
                "node_executions_count": self.node_executions_count,
                "p95_latency_ms": round(self.p95_latency_ms, 2),
                "error_count": self.error_count,
                "total_tokens": self.total_tokens,
            },
        }


@dataclass
class SessionMetricsSummary:
    """Overall session performance summary spanning all completed interview stages."""

    session_id: str
    total_duration_seconds: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_tokens: int = 0
    total_node_runs: int = 0
    average_node_latency_ms: float = 0.0
    stages: dict[str, StageMetricsSummary] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)


class NodeExecutionTracker:
    """Mutable tracker context populated during execution within measure_node_execution."""

    def __init__(self, node_name: str, stage: InterviewStage, model_name: str | None = None) -> None:
        self.node_name = node_name
        self.stage = stage
        self.model_name = model_name
        self.token_usage = TokenUsage()
        self.error_message: str | None = None
        self.is_success = True

    def set_token_usage(
        self,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int | None = None,
    ) -> None:
        """Update token usage counts for this invocation."""
        self.token_usage.prompt_tokens = prompt_tokens
        self.token_usage.completion_tokens = completion_tokens
        self.token_usage.total_tokens = (
            total_tokens if total_tokens is not None else (prompt_tokens + completion_tokens)
        )

    def set_error(self, err: Exception | str) -> None:
        """Mark invocation as failed with an error message."""
        self.is_success = False
        self.error_message = str(err)


class GraphMetricsCollector:
    """In-memory telemetry accumulator for LangGraph nodes during an interview session."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._metrics: list[NodeExecutionMetric] = []
        self._stage_turns: dict[InterviewStage, int] = {}
        self._stage_durations: dict[InterviewStage, float] = {}

    def record_execution(self, metric: NodeExecutionMetric) -> None:
        """Record a completed node execution metric."""
        self._metrics.append(metric)

    def record_node_result(
        self,
        result: NodeResult,
        stage: InterviewStage,
        model_name: str | None = None,
    ) -> None:
        """Record telemetry from a standard NodeResult instance."""
        now = time.time()
        start = now - (result.latency_ms / 1000.0)
        metric = NodeExecutionMetric(
            node_name=result.node_name,
            stage=stage,
            start_time=start,
            end_time=now,
            duration_ms=result.latency_ms,
            token_usage=result.token_usage,
            model_name=model_name,
            is_success=result.is_success,
            error_message=result.error,
        )
        self.record_execution(metric)

    def update_stage_progress(
        self,
        stage: InterviewStage,
        turns: int,
        duration_seconds: float,
    ) -> None:
        """Update external stage turn counts and duration measurements."""
        self._stage_turns[stage] = max(self._stage_turns.get(stage, 0), turns)
        self._stage_durations[stage] = max(self._stage_durations.get(stage, 0.0), duration_seconds)

    def get_stage_summary(self, stage: InterviewStage) -> StageMetricsSummary:
        """Compute aggregated summary for a single interview stage."""
        stage_metrics = [m for m in self._metrics if m.stage == stage]
        if not stage_metrics:
            return StageMetricsSummary(
                stage=stage,
                turn_count=self._stage_turns.get(stage, 0),
                duration_seconds=self._stage_durations.get(stage, 0.0),
            )

        tokens_in = sum(m.token_usage.prompt_tokens for m in stage_metrics)
        tokens_out = sum(m.token_usage.completion_tokens for m in stage_metrics)
        total_tokens = sum(m.token_usage.total_tokens for m in stage_metrics)
        errors = sum(1 for m in stage_metrics if not m.is_success)

        latencies = sorted([m.duration_ms for m in stage_metrics])
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

        p95_idx = max(0, math.ceil(len(latencies) * 0.95) - 1) if latencies else 0
        p95_lat = latencies[p95_idx] if latencies else 0.0

        duration_sec = self._stage_durations.get(stage)
        if duration_sec is None:
            if stage_metrics:
                duration_sec = max(0.0, stage_metrics[-1].end_time - stage_metrics[0].start_time)
            else:
                duration_sec = 0.0

        return StageMetricsSummary(
            stage=stage,
            turn_count=self._stage_turns.get(stage, 0),
            duration_seconds=round(duration_sec, 2),
            token_count_in=tokens_in,
            token_count_out=tokens_out,
            total_tokens=total_tokens,
            node_executions_count=len(stage_metrics),
            average_latency_ms=round(avg_lat, 2),
            p95_latency_ms=round(p95_lat, 2),
            error_count=errors,
        )

    def get_session_summary(self) -> SessionMetricsSummary:
        """Compute aggregated performance summary across all interview stages."""
        stage_summaries: dict[str, StageMetricsSummary] = {}
        all_stages = {m.stage for m in self._metrics} | set(self._stage_turns.keys())

        for stg in all_stages:
            stage_summaries[stg.value] = self.get_stage_summary(stg)

        total_in = sum(s.token_count_in for s in stage_summaries.values())
        total_out = sum(s.token_count_out for s in stage_summaries.values())
        total_tok = sum(s.total_tokens for s in stage_summaries.values())
        total_dur = sum(s.duration_seconds for s in stage_summaries.values())

        latencies = [m.duration_ms for m in self._metrics]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0.0

        errors = [
            m.to_dict()
            for m in self._metrics
            if not m.is_success and m.error_message
        ]

        return SessionMetricsSummary(
            session_id=self.session_id,
            total_duration_seconds=round(total_dur, 2),
            total_tokens_in=total_in,
            total_tokens_out=total_out,
            total_tokens=total_tok,
            total_node_runs=len(self._metrics),
            average_node_latency_ms=round(avg_lat, 2),
            stages=stage_summaries,
            errors=errors,
        )

    def export_stage_metrics_for_db(self, session_id: UUID | str) -> list[dict[str, Any]]:
        """Export all stage summaries in a format ready for StageMetric ORM persistence."""
        summaries = []
        all_stages = {m.stage for m in self._metrics} | set(self._stage_turns.keys())
        for stg in all_stages:
            summary = self.get_stage_summary(stg)
            summaries.append(summary.to_db_dict(session_id))
        return summaries

    def clear(self) -> None:
        """Reset internal metrics storage."""
        self._metrics.clear()
        self._stage_turns.clear()
        self._stage_durations.clear()


# Context variable for thread-local / coroutine-local metrics collector propagation
_CURRENT_COLLECTOR: ContextVar[GraphMetricsCollector | None] = ContextVar(
    "_CURRENT_COLLECTOR",
    default=None,
)


def get_current_metrics_collector() -> GraphMetricsCollector | None:
    """Retrieve active coroutine-scoped GraphMetricsCollector."""
    return _CURRENT_COLLECTOR.get()


def set_current_metrics_collector(
    collector: GraphMetricsCollector | None,
) -> None:
    """Set the active coroutine-scoped GraphMetricsCollector."""
    _CURRENT_COLLECTOR.set(collector)


@asynccontextmanager
async def measure_node_execution(
    collector: GraphMetricsCollector | None,
    node_name: str,
    stage: InterviewStage,
    model_name: str | None = None,
) -> AsyncIterator[NodeExecutionTracker]:
    """Async context manager measuring wall-clock duration and tracking token usage.

    Args:
        collector: Optional collector instance. If None, resolves from coroutine context.
        node_name: Name of the executing StateGraph node.
        stage: Current interview stage.
        model_name: Optional LLM model identifier.

    Yields:
        NodeExecutionTracker to attach token counts and errors during node execution.
    """
    active_collector = collector or get_current_metrics_collector()
    tracker = NodeExecutionTracker(node_name=node_name, stage=stage, model_name=model_name)
    start_time = time.time()

    try:
        yield tracker
    except Exception as exc:
        tracker.set_error(exc)
        raise
    finally:
        end_time = time.time()
        duration_ms = (end_time - start_time) * 1000.0

        if active_collector is not None:
            metric = NodeExecutionMetric(
                node_name=node_name,
                stage=stage,
                start_time=start_time,
                end_time=end_time,
                duration_ms=duration_ms,
                token_usage=tracker.token_usage,
                model_name=tracker.model_name,
                is_success=tracker.is_success,
                error_message=tracker.error_message,
            )
            active_collector.record_execution(metric)

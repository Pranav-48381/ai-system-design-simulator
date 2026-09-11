"""System Design Interview Simulator - Stage Metric Model.

Records stage-level telemetry including execution latency, turn count,
token consumption (prompt and completion), and pacing analytics.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InterviewStage
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InterviewStageDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class StageMetric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Aggregated performance metrics and token telemetry for an interview stage."""

    __tablename__ = "stage_metrics"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[InterviewStage] = mapped_column(
        InterviewStageDBEnum,
        nullable=False,
        index=True,
    )
    turn_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    duration_seconds: Mapped[float] = mapped_column(
        Float,
        default=0.0,
        nullable=False,
    )
    token_count_in: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    token_count_out: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    average_latency_ms: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="stage_metrics",
    )

    __table_args__ = (
        Index("ix_stage_metrics_session_stage", "session_id", "stage", unique=True),
    )

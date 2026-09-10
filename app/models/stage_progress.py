"""System Design Interview Simulator - Session Stage Progress Model.

Tracks per-stage timing, turn expenditure, criteria completion, and status transitions.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InterviewStage
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InterviewStageDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class SessionStageProgress(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Execution status and metrics for an individual interview stage."""

    __tablename__ = "stage_progress"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    stage: Mapped[InterviewStage] = mapped_column(
        InterviewStageDBEnum,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    turns_spent: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    criteria_met: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )
    stage_state: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="stage_progress",
    )

    __table_args__ = (
        Index("ix_stage_progress_session_stage", "session_id", "stage", unique=True),
    )

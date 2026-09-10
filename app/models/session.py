"""System Design Interview Simulator - Interview Session Model.

Represents an interactive, multi-turn interview session between candidate and AI agent.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, JSON
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import (
    InterviewerPersona,
    InterviewStage,
    SeniorityLevel,
    SessionStatus,
)
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import (
    InterviewerPersonaDBEnum,
    InterviewStageDBEnum,
    SeniorityLevelDBEnum,
    SessionStatusDBEnum,
)

if TYPE_CHECKING:
    from app.models.architecture_artifact import CandidateArchitectureArtifact
    from app.models.audit_log import SessionAuditLog
    from app.models.evaluation import InterviewEvaluation
    from app.models.message import InterviewMessage
    from app.models.problem import SystemDesignProblem
    from app.models.rubric import EvaluationRubric
    from app.models.stage_metric import StageMetric
    from app.models.stage_progress import SessionStageProgress
    from app.models.user import User


class InterviewSession(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """Execution instance of an autonomous technical system design interview."""

    __tablename__ = "interview_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    rubric_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rubrics.id", ondelete="SET NULL"),
        nullable=True,
    )
    persona: Mapped[InterviewerPersona] = mapped_column(
        InterviewerPersonaDBEnum,
        default=InterviewerPersona.COLLABORATIVE,
        nullable=False,
    )
    target_level: Mapped[SeniorityLevel] = mapped_column(
        SeniorityLevelDBEnum,
        default=SeniorityLevel.SENIOR,
        nullable=False,
    )
    current_stage: Mapped[InterviewStage] = mapped_column(
        InterviewStageDBEnum,
        default=InterviewStage.CLARIFICATION,
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        SessionStatusDBEnum,
        default=SessionStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    ended_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    total_turns: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    total_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="sessions",
    )
    problem: Mapped["SystemDesignProblem"] = relationship(
        "SystemDesignProblem",
        back_populates="sessions",
    )
    rubric: Mapped["EvaluationRubric | None"] = relationship(
        "EvaluationRubric",
        back_populates="sessions",
    )
    messages: Mapped[list["InterviewMessage"]] = relationship(
        "InterviewMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.sequence_number",
    )
    stage_progress: Mapped[list["SessionStageProgress"]] = relationship(
        "SessionStageProgress",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionStageProgress.created_at",
    )
    artifacts: Mapped[list["CandidateArchitectureArtifact"]] = relationship(
        "CandidateArchitectureArtifact",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="desc(CandidateArchitectureArtifact.created_at)",
    )
    evaluation: Mapped["InterviewEvaluation | None"] = relationship(
        "InterviewEvaluation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list["SessionAuditLog"]] = relationship(
        "SessionAuditLog",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="SessionAuditLog.created_at",
    )
    stage_metrics: Mapped[list["StageMetric"]] = relationship(
        "StageMetric",
        back_populates="session",
        cascade="all, delete-orphan",
    )

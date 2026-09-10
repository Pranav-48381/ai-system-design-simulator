"""System Design Interview Simulator - Interview Evaluation Model.

Stores multi-rubric evaluation scorecards, pillar scores, hiring recommendations,
and synthesis notes produced at the interview debrief stage.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import SeniorityLevel
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import SeniorityLevelDBEnum

if TYPE_CHECKING:
    from app.models.feedback import EvaluationFeedbackItem
    from app.models.session import InterviewSession


class InterviewEvaluation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Holistic evaluation scorecard for a completed or debriefed interview session."""

    __tablename__ = "evaluations"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    overall_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )
    recommended_level: Mapped[SeniorityLevel] = mapped_column(
        SeniorityLevelDBEnum,
        default=SeniorityLevel.SENIOR,
        nullable=False,
    )
    hiring_recommendation: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    pillar_scores: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="evaluation",
    )
    feedback_items: Mapped[list["EvaluationFeedbackItem"]] = relationship(
        "EvaluationFeedbackItem",
        back_populates="evaluation",
        cascade="all, delete-orphan",
        order_by="EvaluationFeedbackItem.created_at",
    )

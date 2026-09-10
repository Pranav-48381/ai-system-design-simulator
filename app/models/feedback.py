"""System Design Interview Simulator - Evaluation Feedback Item Model.

Represents specific positive feedback, growth areas, missing architectural elements,
and tailored learning resources generated during candidate evaluation.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ScoringPillar
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import FeedbackCategory, FeedbackCategoryDBEnum, ScoringPillarDBEnum

if TYPE_CHECKING:
    from app.models.evaluation import InterviewEvaluation


class EvaluationFeedbackItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Detailed observation item contributing to the final interview debrief."""

    __tablename__ = "feedback_items"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[FeedbackCategory] = mapped_column(
        FeedbackCategoryDBEnum,
        default=FeedbackCategory.IMPROVEMENT,
        nullable=False,
    )
    pillar: Mapped[ScoringPillar | None] = mapped_column(
        ScoringPillarDBEnum,
        nullable=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    detail: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    resources: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )

    # Relationships
    evaluation: Mapped["InterviewEvaluation"] = relationship(
        "InterviewEvaluation",
        back_populates="feedback_items",
    )

    __table_args__ = (
        Index("ix_feedback_eval_category", "evaluation_id", "category"),
    )

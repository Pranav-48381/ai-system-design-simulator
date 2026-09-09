"""System Design Interview Simulator - Evaluation Rubric Models.

Defines rubric blueprints and competency criteria used to grade candidates across
the 5 core system design pillars.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, Float, ForeignKey, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ScoringPillar
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ScoringPillarDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class EvaluationRubric(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Container for a cohesive set of system design scoring criteria."""

    __tablename__ = "rubrics"

    name: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    # Relationships
    criteria: Mapped[list["RubricCriterion"]] = relationship(
        "RubricCriterion",
        back_populates="rubric",
        cascade="all, delete-orphan",
        order_by="RubricCriterion.pillar",
    )
    sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="rubric",
    )


class RubricCriterion(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific scoring criterion aligned to an evaluation pillar."""

    __tablename__ = "rubric_criteria"

    rubric_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rubrics.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pillar: Mapped[ScoringPillar] = mapped_column(
        ScoringPillarDBEnum,
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
    )
    level_expectations: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    rubric: Mapped["EvaluationRubric"] = relationship(
        "EvaluationRubric",
        back_populates="criteria",
    )

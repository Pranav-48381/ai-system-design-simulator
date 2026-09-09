"""System Design Interview Simulator - System Design Problem Model.

Defines the structure of interview problem definitions, requirements, scale targets,
and architectural challenges.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ProblemDifficulty
from app.db.base import Base
from app.db.mixins import SoftDeleteMixin, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ProblemDifficultyDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession
    from app.models.tag import ProblemTag


class SystemDesignProblem(Base, UUIDPrimaryKeyMixin, TimestampMixin, SoftDeleteMixin):
    """System design interview question definition and reference specification."""

    __tablename__ = "problems"

    slug: Mapped[str] = mapped_column(
        String(128),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    difficulty: Mapped[ProblemDifficulty] = mapped_column(
        ProblemDifficultyDBEnum,
        default=ProblemDifficulty.MEDIUM,
        nullable=False,
    )
    functional_requirements: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )
    non_functional_requirements: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )
    scale_targets: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )
    key_challenges: Mapped[list[str]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=list,
        nullable=False,
    )
    reference_solution: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        nullable=True,
        default=None,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    tags: Mapped[list["ProblemTag"]] = relationship(
        "ProblemTag",
        secondary="problem_tag_associations",
        back_populates="problems",
    )
    sessions: Mapped[list["InterviewSession"]] = relationship(
        "InterviewSession",
        back_populates="problem",
    )

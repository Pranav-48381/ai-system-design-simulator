"""System Design Interview Simulator - Problem Tag Model.

Represents architectural tags and concepts associated with system design questions.
"""

from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.problem import SystemDesignProblem


class ProblemTag(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Architectural classification tag (e.g., 'distributed-cache', 'rate-limiter')."""

    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    problems: Mapped[list["SystemDesignProblem"]] = relationship(
        "SystemDesignProblem",
        secondary="problem_tag_associations",
        back_populates="tags",
    )

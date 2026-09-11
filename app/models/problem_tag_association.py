"""System Design Interview Simulator - Problem Tag Association.

Associates system design problems with classification tags (e.g. Distributed, Caching, Event-Driven).
"""

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ProblemTagAssociation(Base):
    """Many-to-many junction table between SystemDesignProblem and ProblemTag."""

    __tablename__ = "problem_tag_associations"

    problem_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("problems.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )

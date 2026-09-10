"""System Design Interview Simulator - Interview Message Model.

Stores chronological dialogue turns exchanged between candidate, AI interviewer,
and system announcements during the interview.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import Float, ForeignKey, Index, Integer, JSON, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InterviewStage, SpeakerRole
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import InterviewStageDBEnum, SpeakerRoleDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class InterviewMessage(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Granular dialogue turn in an interview session."""

    __tablename__ = "interview_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    role: Mapped[SpeakerRole] = mapped_column(
        SpeakerRoleDBEnum,
        nullable=False,
    )
    stage: Mapped[InterviewStage] = mapped_column(
        InterviewStageDBEnum,
        nullable=False,
        index=True,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    token_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    latency_ms: Mapped[float | None] = mapped_column(
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
        back_populates="messages",
    )

    __table_args__ = (
        Index("ix_messages_session_seq", "session_id", "sequence_number"),
    )

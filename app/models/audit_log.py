"""System Design Interview Simulator - Session Audit Log Model.

Records state transitions, user actions, system events, and stage boundaries
for interview observability, replayability, and analytics.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, JSON, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InterviewStage
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import AuditEventType, AuditEventTypeDBEnum, InterviewStageDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class SessionAuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit trail for interview session events and state transitions."""

    __tablename__ = "session_audit_logs"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[AuditEventType] = mapped_column(
        AuditEventTypeDBEnum,
        nullable=False,
        index=True,
    )
    stage: Mapped[InterviewStage | None] = mapped_column(
        InterviewStageDBEnum,
        nullable=True,
        index=True,
    )
    action: Mapped[str | None] = mapped_column(
        String(128),
        nullable=True,
    )
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    # Relationships
    session: Mapped["InterviewSession"] = relationship(
        "InterviewSession",
        back_populates="audit_logs",
    )

    __table_args__ = (
        Index("ix_audit_logs_session_created", "session_id", "created_at"),
    )

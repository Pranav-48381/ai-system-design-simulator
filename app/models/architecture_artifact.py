"""System Design Interview Simulator - Architecture Artifact Model.

Stores whiteboard architecture diagrams (Mermaid), API design specs, data models,
and capacity calculation worksheets submitted during an interview session.
"""

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import ArtifactType
from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import ArtifactTypeDBEnum

if TYPE_CHECKING:
    from app.models.session import InterviewSession


class CandidateArchitectureArtifact(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Visual or structured artifact (e.g., Mermaid diagram, schema, API contract)."""

    __tablename__ = "architecture_artifacts"

    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(
        ArtifactTypeDBEnum,
        default=ArtifactType.ARCHITECTURE_DIAGRAM,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
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
        back_populates="artifacts",
    )

    __table_args__ = (
        Index("ix_artifacts_session_type", "session_id", "artifact_type"),
    )

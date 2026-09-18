"""System Design Interview Simulator - Architecture Artifact Repository.

Provides specialized asynchronous data access operations for candidate whiteboard artifacts,
including versioned Mermaid architecture diagrams, API definitions, data models, and estimation sheets.
"""

from collections.abc import Sequence
from typing import Any
import uuid

from sqlalchemy import delete as sql_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import ArtifactType
from app.core.exceptions import EntityNotFoundError
from app.core.logging import get_logger
from app.models.architecture_artifact import CandidateArchitectureArtifact
from app.repositories.base import BaseRepository

logger = get_logger(__name__)


class ArtifactRepository(BaseRepository[CandidateArchitectureArtifact]):
    """Repository handling versioned persistence and retrieval for candidate architecture artifacts."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize ArtifactRepository with active AsyncSession."""
        super().__init__(CandidateArchitectureArtifact, session)

    async def get_latest_by_type(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType,
    ) -> CandidateArchitectureArtifact | None:
        """Retrieve the latest version of a specific artifact type for a session.

        Args:
            session_id: Interview session UUID.
            artifact_type: Artifact type (e.g. ARCHITECTURE_DIAGRAM, API_DESIGN).

        Returns:
            The most recent CandidateArchitectureArtifact instance, or None.
        """
        stmt = (
            select(CandidateArchitectureArtifact)
            .where(
                CandidateArchitectureArtifact.session_id == session_id,
                CandidateArchitectureArtifact.artifact_type == artifact_type,
            )
            .order_by(CandidateArchitectureArtifact.version.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_type_or_raise(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType,
    ) -> CandidateArchitectureArtifact:
        """Retrieve the latest artifact version or raise EntityNotFoundError.

        Args:
            session_id: Interview session UUID.
            artifact_type: Target ArtifactType.

        Returns:
            The CandidateArchitectureArtifact instance.

        Raises:
            EntityNotFoundError: If no artifact of this type exists for the session.
        """
        artifact = await self.get_latest_by_type(session_id, artifact_type)
        if artifact is None:
            raise EntityNotFoundError(
                entity_name="CandidateArchitectureArtifact",
                entity_id=f"session_{session_id}_{artifact_type.value}",
            )
        return artifact

    async def get_version(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType,
        version: int,
    ) -> CandidateArchitectureArtifact | None:
        """Retrieve a specific historical version snapshot of an artifact.

        Args:
            session_id: Session UUID.
            artifact_type: ArtifactType enum.
            version: Historical version number.

        Returns:
            The historical CandidateArchitectureArtifact record, or None.
        """
        stmt = select(CandidateArchitectureArtifact).where(
            CandidateArchitectureArtifact.session_id == session_id,
            CandidateArchitectureArtifact.artifact_type == artifact_type,
            CandidateArchitectureArtifact.version == version,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def save_version(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType,
        title: str,
        content: str,
        metadata_json: dict[str, Any] | None = None,
    ) -> CandidateArchitectureArtifact:
        """Save a new version snapshot of an architectural artifact.

        Automatically computes the next sequential version number for the given session and artifact type.

        Args:
            session_id: Target interview session UUID.
            artifact_type: Category of artifact.
            title: Descriptive title (e.g. "High-Level Microservice Diagram").
            content: Raw diagram syntax (Mermaid), schema DDL, or specification.
            metadata_json: Optional diagram layout or tooling metadata.

        Returns:
            The persisted CandidateArchitectureArtifact instance.
        """
        latest = await self.get_latest_by_type(session_id, artifact_type)
        next_version = (latest.version + 1) if latest is not None else 1

        artifact = CandidateArchitectureArtifact(
            session_id=session_id,
            artifact_type=artifact_type,
            title=title.strip(),
            content=content.strip(),
            version=next_version,
            metadata_json=metadata_json or {},
        )
        persisted = await self.create(artifact, flush=True)
        logger.info(
            "Saved artifact '%s' (type: %s, version: %d, session: %s)",
            persisted.title,
            artifact_type.value,
            next_version,
            session_id,
        )
        return persisted

    async def list_by_session(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType | None = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Sequence[CandidateArchitectureArtifact]:
        """Query artifacts created within an interview session.

        Args:
            session_id: Interview session UUID.
            artifact_type: Optional artifact type filter.
            skip: Offset number.
            limit: Maximum items to return.

        Returns:
            Sequence of CandidateArchitectureArtifact records.
        """
        stmt = (
            select(CandidateArchitectureArtifact)
            .where(CandidateArchitectureArtifact.session_id == session_id)
            .order_by(CandidateArchitectureArtifact.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        if artifact_type is not None:
            stmt = stmt.where(CandidateArchitectureArtifact.artifact_type == artifact_type)

        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def list_version_history(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType,
    ) -> Sequence[CandidateArchitectureArtifact]:
        """Query the full chronological version history of an artifact type.

        Args:
            session_id: Session UUID.
            artifact_type: Target ArtifactType.

        Returns:
            Sequence of artifact versions ordered by version ascending.
        """
        stmt = (
            select(CandidateArchitectureArtifact)
            .where(
                CandidateArchitectureArtifact.session_id == session_id,
                CandidateArchitectureArtifact.artifact_type == artifact_type,
            )
            .order_by(CandidateArchitectureArtifact.version.asc())
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def count_by_session(
        self,
        session_id: uuid.UUID,
        artifact_type: ArtifactType | None = None,
    ) -> int:
        """Count total artifacts for a session.

        Args:
            session_id: Session UUID.
            artifact_type: Optional artifact type filter.

        Returns:
            Total integer count.
        """
        stmt = (
            select(func.count())
            .select_from(CandidateArchitectureArtifact)
            .where(CandidateArchitectureArtifact.session_id == session_id)
        )
        if artifact_type is not None:
            stmt = stmt.where(CandidateArchitectureArtifact.artifact_type == artifact_type)

        result = await self._session.execute(stmt)
        return result.scalar_one() or 0

    async def delete_by_session(self, session_id: uuid.UUID) -> int:
        """Delete all artifacts associated with an interview session.

        Args:
            session_id: Session UUID.

        Returns:
            Count of deleted records.
        """
        stmt = (
            sql_delete(CandidateArchitectureArtifact)
            .where(CandidateArchitectureArtifact.session_id == session_id)
            .execution_options(synchronize_session="fetch")
        )
        result = await self._session.execute(stmt)
        deleted = result.rowcount or 0
        logger.info("Deleted %d artifacts for session %s", deleted, session_id)
        return deleted

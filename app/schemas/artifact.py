"""System Design Interview Simulator - Architecture Artifact Schemas.

Defines Pydantic schemas for candidate-generated whiteboard architecture diagrams,
data models, API specifications, calculation worksheets, and design artifacts.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import ArtifactType
from app.schemas import BaseSchema

# Re-export ArtifactType as ArtifactTypeEnum for explicit schema typing
ArtifactTypeEnum = ArtifactType


class ArtifactBase(BaseSchema):
    """Core attributes common to architecture artifact representations."""

    artifact_type: ArtifactType = Field(
        default=ArtifactType.ARCHITECTURE_DIAGRAM,
        description="Classification of the technical design artifact.",
        examples=[ArtifactType.ARCHITECTURE_DIAGRAM],
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Descriptive title of the architectural artifact.",
        examples=["High-Level Microservices Architecture"],
    )
    content: str = Field(
        ...,
        description="Raw artifact payload (e.g. Mermaid flowchart, JSON schema, SQL DDL).",
        examples=["graph TD; Client-->API_Gateway; API_Gateway-->AuthService;"],
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary structured metadata such as canvas coordinates or viewport zoom.",
    )


class ArtifactCreate(ArtifactBase):
    """Payload for creating a new candidate architecture artifact."""

    session_id: uuid.UUID = Field(
        ...,
        description="Interview session UUID to which this artifact is associated.",
    )


class ArtifactUpdate(BaseSchema):
    """Payload for modifying an existing candidate architecture artifact."""

    title: str | None = Field(
        default=None,
        max_length=255,
        description="Updated title of the artifact.",
    )
    content: str | None = Field(
        default=None,
        description="Updated diagram syntax, schema text, or calculation notes.",
    )
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        description="Updated canvas rendering metadata or viewport state.",
    )


class ArtifactRead(ArtifactBase):
    """Complete candidate architecture artifact model returned across API queries."""

    id: uuid.UUID = Field(description="Unique artifact record UUID.")
    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    version: int = Field(default=1, description="Sequential artifact revision number.")
    created_at: datetime = Field(description="Artifact creation timestamp.")
    updated_at: datetime = Field(description="Last artifact modification timestamp.")


class ArtifactSummary(BaseSchema):
    """Lightweight metadata overview of an artifact without large content payloads."""

    id: uuid.UUID = Field(description="Unique artifact UUID.")
    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    artifact_type: ArtifactType = Field(description="Type of artifact.")
    title: str = Field(description="Artifact title.")
    version: int = Field(description="Artifact version.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")


class ArtifactListRead(BaseSchema):
    """Collection wrapper for session architecture artifacts."""

    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    artifacts: list[ArtifactRead] = Field(
        default_factory=list,
        description="List of architecture artifacts associated with the session.",
    )
    total_count: int = Field(
        default=0,
        description="Total number of artifacts in the session.",
    )

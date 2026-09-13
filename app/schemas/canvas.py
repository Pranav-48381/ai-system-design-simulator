"""System Design Interview Simulator - Whiteboard Canvas Schemas.

Defines Pydantic schemas for real-time collaborative whiteboard synchronizations,
visual architecture diagram nodes, communication edges, and Mermaid-to-canvas representations.
"""

from enum import StrEnum
from datetime import datetime, timezone
from typing import Any
import uuid
from pydantic import Field

from app.schemas import BaseSchema


class DiagramNodeTypeEnum(StrEnum):
    """Architectural classification of components on the whiteboard."""

    CLIENT = "client"
    LOAD_BALANCER = "load_balancer"
    API_GATEWAY = "api_gateway"
    SERVICE = "service"
    DATABASE = "database"
    CACHE = "cache"
    QUEUE = "queue"
    STORAGE = "storage"
    CDN = "cdn"
    CUSTOM = "custom"


class DiagramEdgeTypeEnum(StrEnum):
    """Communication paradigm and protocol between architectural components."""

    SYNC_HTTP = "sync_http"
    ASYNC_MESSAGE = "async_message"
    GRPC = "grpc"
    WEBSOCKET = "websocket"
    DATABASE_QUERY = "database_query"
    REPLICATION = "replication"


class DiagramNodeSchema(BaseSchema):
    """Visual component node rendered on the system design whiteboard."""

    id: str = Field(
        ...,
        description="Unique identifier for the node within the canvas.",
        examples=["srv-auth-01"],
    )
    label: str = Field(
        ...,
        description="Display label or title for the component.",
        examples=["Authentication Service"],
    )
    node_type: DiagramNodeTypeEnum = Field(
        default=DiagramNodeTypeEnum.SERVICE,
        description="Architectural component classification.",
        examples=[DiagramNodeTypeEnum.SERVICE],
    )
    technology: str | None = Field(
        default=None,
        description="Specific framework, database engine, or cloud primitive.",
        examples=["Go + Gin", "PostgreSQL 16"],
    )
    x: float = Field(
        default=0.0,
        description="Horizontal position coordinate on canvas grid.",
    )
    y: float = Field(
        default=0.0,
        description="Vertical position coordinate on canvas grid.",
    )
    width: float | None = Field(
        default=None,
        description="Component width in canvas pixels.",
    )
    height: float | None = Field(
        default=None,
        description="Component height in canvas pixels.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary styling, cluster node count, or SLA annotations.",
    )


class DiagramEdgeSchema(BaseSchema):
    """Directed connection or network flow between two canvas nodes."""

    id: str = Field(
        ...,
        description="Unique edge identifier within canvas.",
        examples=["edge-client-gw"],
    )
    source_node_id: str = Field(
        ...,
        description="Source component node ID.",
        examples=["client-mobile"],
    )
    target_node_id: str = Field(
        ...,
        description="Destination component node ID.",
        examples=["api-gw"],
    )
    label: str | None = Field(
        default=None,
        description="Protocol, endpoint, or payload summary describing the traffic.",
        examples=["HTTPS /v1/auth/login"],
    )
    edge_type: DiagramEdgeTypeEnum = Field(
        default=DiagramEdgeTypeEnum.SYNC_HTTP,
        description="Communication flow classification.",
        examples=[DiagramEdgeTypeEnum.SYNC_HTTP],
    )
    is_bidirectional: bool = Field(
        default=False,
        description="True if traffic flows symmetrically in both directions.",
    )


class WhiteboardCanvasState(BaseSchema):
    """Holistic state snapshot of the architectural whiteboard canvas."""

    session_id: uuid.UUID = Field(
        ...,
        description="Associated interview session UUID.",
    )
    version: int = Field(
        default=1,
        ge=1,
        description="Monotonically increasing canvas revision number.",
    )
    title: str = Field(
        default="System Architecture Diagram",
        max_length=255,
        description="Descriptive title of the diagram canvas.",
    )
    mermaid_code: str | None = Field(
        default=None,
        description="Mermaid diagram textual syntax corresponding to the canvas.",
        examples=["graph TD; Client-->API_Gateway; API_Gateway-->Auth_Service;"],
    )
    nodes: list[DiagramNodeSchema] = Field(
        default_factory=list,
        description="List of architectural nodes positioned on the whiteboard.",
    )
    edges: list[DiagramEdgeSchema] = Field(
        default_factory=list,
        description="List of directed communication edges connecting nodes.",
    )
    viewport: dict[str, Any] = Field(
        default_factory=dict,
        description="Canvas pan coordinates and zoom scale factor.",
    )


class WhiteboardSyncEvent(BaseSchema):
    """Event emitted when candidate or agent updates the whiteboard canvas."""

    event_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique event synchronization ID.",
    )
    session_id: uuid.UUID = Field(
        ...,
        description="Interview session UUID.",
    )
    version: int = Field(
        ...,
        ge=1,
        description="Canvas revision version resulting from this event.",
    )
    action: str = Field(
        ...,
        description="Synchronization action type (full_replace, node_upsert, node_delete, edge_upsert).",
        examples=["full_replace"],
    )
    state: WhiteboardCanvasState = Field(
        ...,
        description="Resulting whiteboard state snapshot.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the synchronization event.",
    )

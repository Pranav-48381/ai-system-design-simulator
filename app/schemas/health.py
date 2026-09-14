"""System Design Interview Simulator - Health Check & Observability Schemas.

Defines Pydantic schemas for multi-component health checks, readiness/liveness probes,
subsystem latency metrics (database, LLMs, checkpointer, websockets), and telemetry reporting.
"""

from enum import StrEnum
from datetime import datetime, timezone
from typing import Any
from pydantic import Field

from app.schemas import BaseSchema


class HealthStatusEnum(StrEnum):
    """Aggregate or component-level health status."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentTypeEnum(StrEnum):
    """Classification of internal subsystem or external infrastructure dependency."""

    DATABASE = "database"
    CACHE = "cache"
    LLM_PROVIDER = "llm_provider"
    WEBSOCKET_MANAGER = "websocket_manager"
    CHECKPOINTER = "checkpointer"
    STORAGE = "storage"
    BACKGROUND_WORKER = "background_worker"


class ComponentHealthSchema(BaseSchema):
    """Granular health status and diagnostics for an individual subsystem."""

    name: str = Field(
        ...,
        description="Subsystem or service name.",
        examples=["PostgreSQL Primary Connection Pool"],
    )
    component_type: ComponentTypeEnum = Field(
        ...,
        description="Architectural component classification.",
        examples=[ComponentTypeEnum.DATABASE],
    )
    status: HealthStatusEnum = Field(
        ...,
        description="Current operational health condition.",
        examples=[HealthStatusEnum.HEALTHY],
    )
    is_critical: bool = Field(
        default=True,
        description="True if degradation of this component marks the overall service unhealthy.",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Response or ping latency in milliseconds.",
        examples=[3.25],
    )
    details: dict[str, Any] = Field(
        default_factory=dict,
        description="Subsystem-specific diagnostic properties (e.g. pool size, version, quota).",
        examples=[{"pool_size": 10, "overflow": 0, "active_connections": 2}],
    )
    error_message: str | None = Field(
        default=None,
        description="Error detail or exception traceback if component is degraded/unhealthy.",
    )
    checked_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when probe was executed.",
    )


class SystemMetricsSchema(BaseSchema):
    """Runtime process and resource utilization telemetry."""

    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Process uptime in elapsed seconds.",
        examples=[3600.5],
    )
    cpu_usage_percent: float | None = Field(
        default=None,
        ge=0.0,
        le=100.0,
        description="Current CPU usage percentage of the application worker.",
        examples=[14.2],
    )
    memory_usage_mb: float | None = Field(
        default=None,
        ge=0.0,
        description="Resident set size (RSS) memory consumption in Megabytes.",
        examples=[184.6],
    )
    active_websocket_connections: int = Field(
        default=0,
        ge=0,
        description="Count of currently active candidate WebSocket client connections.",
        examples=[4],
    )
    active_interview_sessions: int = Field(
        default=0,
        ge=0,
        description="Count of interview sessions currently in progress.",
        examples=[2],
    )


class HealthCheckResponse(BaseSchema):
    """Detailed health check report across all system dependencies and resources."""

    status: HealthStatusEnum = Field(
        ...,
        description="Overall service operational health verdict.",
        examples=[HealthStatusEnum.HEALTHY],
    )
    service_name: str = Field(
        default="ai-system-design-simulator",
        description="Application service identifier.",
    )
    version: str = Field(
        default="0.1.0",
        description="Deployed semantic version.",
        examples=["0.1.0"],
    )
    environment: str = Field(
        default="production",
        description="Active deployment runtime environment.",
        examples=["production"],
    )
    uptime_seconds: float = Field(
        ...,
        ge=0.0,
        description="Server process uptime in seconds.",
        examples=[7200.0],
    )
    components: list[ComponentHealthSchema] = Field(
        default_factory=list,
        description="Health states of individual dependencies and subsystems.",
    )
    system_metrics: SystemMetricsSchema | None = Field(
        default=None,
        description="Runtime system resource consumption metrics.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the health check evaluation.",
    )


class ReadinessProbeResponse(BaseSchema):
    """Kubernetes / container readiness probe response indicating traffic eligibility."""

    ready: bool = Field(
        ...,
        description="Whether application is ready to accept incoming client traffic.",
        examples=[True],
    )
    dependencies_ready: bool = Field(
        ...,
        description="Whether all critical external backing dependencies are verified reachable.",
    )
    database_connected: bool = Field(
        ...,
        description="PostgreSQL connectivity confirmation.",
    )
    llm_configured: bool = Field(
        ...,
        description="At least one LLM client provider configured with valid API keys.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC evaluation timestamp.",
    )


class LivenessProbeResponse(BaseSchema):
    """Kubernetes / container liveness probe verifying event loop responsiveness."""

    alive: bool = Field(
        default=True,
        description="Process responsiveness flag.",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC evaluation timestamp.",
    )

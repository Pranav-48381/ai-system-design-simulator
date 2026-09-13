"""System Design Interview Simulator - Token Streaming Schemas.

Defines Pydantic schemas for async token stream chunks, event framing,
streaming telemetry metrics, and lifecycle events between LangGraph nodes and API/WebSocket consumers.
"""

from enum import StrEnum
from datetime import datetime, timezone
from typing import Any
import uuid
from pydantic import Field

from app.core.constants import InterviewStage
from app.schemas import BaseSchema


class StreamEventTypeEnum(StrEnum):
    """Event classification types emitted across LLM token streaming pipelines."""

    TOKEN = "token"
    START = "start"
    END = "end"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    STAGE_SIGNAL = "stage_signal"
    METRICS = "metrics"


class TokenStreamChunk(BaseSchema):
    """Granular token chunk yielded during asynchronous LLM generation."""

    event: StreamEventTypeEnum = Field(
        default=StreamEventTypeEnum.TOKEN,
        description="Stream event type discriminator.",
        examples=[StreamEventTypeEnum.TOKEN],
    )
    token: str = Field(
        default="",
        description="Text content of the streamed chunk or fragment.",
        examples=["Let's analyze "],
    )
    index: int = Field(
        default=0,
        ge=0,
        description="Zero-indexed sequence number of the chunk in the active generation turn.",
    )
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Interview session UUID.",
    )
    message_id: uuid.UUID | None = Field(
        default=None,
        description="Interview message UUID associated with this generation stream.",
    )
    stage: InterviewStage | None = Field(
        default=None,
        description="Active interview stage when the chunk was generated.",
    )
    is_final: bool = Field(
        default=False,
        description="True if this chunk marks the completion of the streaming turn.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Auxiliary generation metadata, such as token logprobs or latency metrics.",
    )


class StreamStartEvent(BaseSchema):
    """Event emitted at the onset of an interviewer response stream."""

    session_id: uuid.UUID = Field(description="Interview session UUID.")
    message_id: uuid.UUID = Field(description="New message UUID allocated for the generation.")
    stage: InterviewStage = Field(description="Active interview stage.")
    role: str = Field(default="interviewer", description="Speaker role.")
    model_name: str | None = Field(
        default=None,
        description="Model identifier powering the generation (e.g. gpt-4o, claude-3-5-sonnet).",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when streaming commenced.",
    )


class StreamEndEvent(BaseSchema):
    """Event emitted upon completion of an interviewer response stream."""

    session_id: uuid.UUID = Field(description="Interview session UUID.")
    message_id: uuid.UUID = Field(description="Message UUID that finished generating.")
    full_text: str = Field(description="Aggregated final text content of the message.")
    total_tokens: int = Field(
        default=0,
        description="Total tokens produced in this response turn.",
    )
    duration_ms: float = Field(
        default=0.0,
        description="Total elapsed generation time in milliseconds.",
    )
    finish_reason: str = Field(
        default="stop",
        description="LLM generation termination reason (stop, length, tool_calls).",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp when streaming completed.",
    )


class StreamMetricsEvent(BaseSchema):
    """Telemetry metrics emitted for real-time observability of token streaming performance."""

    session_id: uuid.UUID = Field(description="Interview session UUID.")
    message_id: uuid.UUID = Field(description="Message UUID.")
    time_to_first_token_ms: float | None = Field(
        default=None,
        description="Latency from stream request initiation to first token chunk arrival in ms.",
    )
    tokens_per_second: float | None = Field(
        default=None,
        description="Effective token throughput rate during active streaming.",
    )
    total_tokens: int = Field(
        default=0,
        description="Total token count consumed.",
    )
    total_duration_ms: float = Field(
        default=0.0,
        description="Total duration in milliseconds.",
    )

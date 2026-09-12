"""System Design Interview Simulator - Interview Message Schemas and DTOs.

Defines Pydantic models for turn-by-turn dialogue, candidate responses, interviewer
critiques, and chronological conversation history.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import InterviewStage, SpeakerRole
from app.schemas import BaseSchema


class MessageBase(BaseSchema):
    """Core attributes common to interview conversation messages."""

    role: SpeakerRole = Field(
        ...,
        description="Speaker identity (candidate, interviewer, or system).",
        examples=[SpeakerRole.CANDIDATE],
    )
    stage: InterviewStage = Field(
        ...,
        description="Interview stage during which this message was generated.",
        examples=[InterviewStage.CLARIFICATION],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Text content of the dialogue turn or system announcement.",
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary turn telemetry (LLM model name, intent classification, prompt tokens).",
    )


class MessageCreate(MessageBase):
    """Schema for persisting a new dialogue turn in an interview session."""

    session_id: uuid.UUID = Field(
        ...,
        description="Parent interview session UUID.",
    )
    sequence_number: int | None = Field(
        default=None,
        ge=1,
        description="1-based sequence order index (auto-computed by repository if omitted).",
    )
    token_count: int | None = Field(
        default=None,
        ge=0,
        description="Token count consumed in generating or transmitting this message.",
    )
    latency_ms: float | None = Field(
        default=None,
        ge=0.0,
        description="Inference response generation latency in milliseconds.",
    )


class CandidateTurnInput(BaseSchema):
    """Simplified payload submitted by a candidate during an active interview."""

    content: str = Field(
        ...,
        min_length=1,
        description="Candidate's technical answer, clarification query, or architectural explanation.",
        examples=["Should the URL shortener support custom aliases chosen by users?"],
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Optional client telemetry or canvas interaction attachments.",
    )


class MessageRead(MessageBase):
    """Full representation of a persisted interview dialogue turn."""

    id: uuid.UUID = Field(description="Unique message identifier.")
    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    sequence_number: int = Field(description="1-based sequential position in dialogue flow.")
    token_count: int | None = Field(default=None, description="Number of tokens used.")
    latency_ms: float | None = Field(default=None, description="Generation latency in ms.")
    created_at: datetime = Field(description="UTC timestamp when turn occurred.")
    updated_at: datetime = Field(description="Last record modification timestamp.")


class MessageHistory(BaseSchema):
    """Chronological conversation history for an interview session."""

    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    total_messages: int = Field(description="Total message count in the history.")
    messages: list[MessageRead] = Field(
        default_factory=list,
        description="Ordered list of dialogue messages.",
    )


class MessageFilterParams(BaseSchema):
    """Query parameters for filtering session message history."""

    stage: InterviewStage | None = Field(default=None, description="Filter turns by stage.")
    role: SpeakerRole | None = Field(default=None, description="Filter turns by speaker role.")

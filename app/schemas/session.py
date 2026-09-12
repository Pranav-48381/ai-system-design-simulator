"""System Design Interview Simulator - Interview Session Schemas and DTOs.

Defines Pydantic schemas for interview session initialization, stage progression,
lifecycle status updates, and session telemetry representations.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import (
    InterviewerPersona,
    InterviewStage,
    SeniorityLevel,
    SessionStatus,
)
from app.schemas import BaseSchema
from app.schemas.problem import ProblemSummary
from app.schemas.rubric import RubricRead
from app.schemas.user import UserSummary


class SessionBase(BaseSchema):
    """Core attributes common to interview session creation and responses."""

    problem_id: uuid.UUID = Field(
        ...,
        description="UUID of the system design problem selected for the interview.",
    )
    persona: InterviewerPersona = Field(
        default=InterviewerPersona.COLLABORATIVE,
        description="Behavioral persona and interrogation style of the AI interviewer.",
        examples=[InterviewerPersona.COLLABORATIVE],
    )
    target_level: SeniorityLevel = Field(
        default=SeniorityLevel.SENIOR,
        description="Target engineering seniority level for calibrated evaluation.",
        examples=[SeniorityLevel.SENIOR],
    )
    rubric_id: uuid.UUID | None = Field(
        default=None,
        description="Optional custom scoring rubric identifier; falls back to default if null.",
    )


class SessionCreate(SessionBase):
    """Schema for initializing a new autonomous interview session."""

    user_id: uuid.UUID | None = Field(
        default=None,
        description="Candidate user UUID (typically inferred from active authentication context).",
    )


class SessionStatusUpdate(BaseSchema):
    """Schema for manually updating the session operational lifecycle status."""

    status: SessionStatus = Field(
        ...,
        description="Target status to transition the session into (e.g. IN_PROGRESS, PAUSED, COMPLETED).",
        examples=[SessionStatus.IN_PROGRESS],
    )


class SessionStageTransition(BaseSchema):
    """Payload requesting an explicit transition between interview stages."""

    target_stage: InterviewStage = Field(
        ...,
        description="Next interview stage to transition the state machine into.",
        examples=[InterviewStage.ESTIMATION],
    )
    reason: str | None = Field(
        default=None,
        description="Optional justification or triggering event for transitioning stages early.",
    )


class SessionRead(SessionBase):
    """Standard interview session state model returned across API queries."""

    id: uuid.UUID = Field(description="Unique interview session UUID.")
    user_id: uuid.UUID = Field(description="UUID of the candidate user.")
    current_stage: InterviewStage = Field(description="Currently active interview stage.")
    status: SessionStatus = Field(description="Current operational lifecycle status.")
    started_at: datetime | None = Field(default=None, description="UTC timestamp when interview commenced.")
    ended_at: datetime | None = Field(default=None, description="UTC timestamp when interview concluded.")
    total_turns: int = Field(default=0, description="Cumulative count of dialogue turns exchanged.")
    total_duration_seconds: int = Field(default=0, description="Cumulative active interview duration in seconds.")
    metadata_json: dict[str, Any] = Field(default_factory=dict, description="Session configuration and telemetry.")
    created_at: datetime = Field(description="Session creation timestamp.")
    updated_at: datetime = Field(description="Last state update timestamp.")


class SessionSummary(BaseSchema):
    """Compact session representation for candidate dashboard history lists."""

    id: uuid.UUID = Field(description="Interview session UUID.")
    problem_id: uuid.UUID = Field(description="Problem UUID.")
    problem_title: str | None = Field(default=None, description="Problem title if joined.")
    current_stage: InterviewStage = Field(description="Current stage.")
    status: SessionStatus = Field(description="Status.")
    target_level: SeniorityLevel = Field(description="Candidate target level.")
    persona: InterviewerPersona = Field(description="Interviewer style.")
    total_turns: int = Field(description="Dialogue turns.")
    total_duration_seconds: int = Field(description="Duration in seconds.")
    created_at: datetime = Field(description="Creation timestamp.")


class SessionDetailRead(SessionRead):
    """Comprehensive interview session representation with nested entity associations."""

    user: UserSummary | None = Field(default=None, description="Candidate profile summary.")
    problem: ProblemSummary | None = Field(default=None, description="Problem definition summary.")
    rubric: RubricRead | None = Field(default=None, description="Evaluation rubric metadata.")

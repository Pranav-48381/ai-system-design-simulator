"""System Design Interview Simulator - Stage Progress and Transition Schemas.

Defines Pydantic schemas for stage state machine transitions, stage progress tracking,
criteria satisfaction, and aggregate stage lifecycle status representations.
"""

from enum import StrEnum
import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import (
    INTERVIEW_STAGE_DESCRIPTIONS,
    INTERVIEW_STAGE_ORDER,
    INTERVIEW_STAGE_TITLES,
    InterviewStage,
)
from app.schemas import BaseSchema


class StageStatusEnum(StrEnum):
    """Execution status for an individual interview stage."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class StageTransitionRequest(BaseSchema):
    """Payload for requesting an explicit state machine stage transition."""

    target_stage: InterviewStage = Field(
        ...,
        description="Target interview stage to transition the state machine into.",
        examples=[InterviewStage.ESTIMATION],
    )
    reason: str | None = Field(
        default=None,
        description="Optional justification or triggering event for transitioning stages.",
        examples=["Candidate completed all functional and non-functional requirements."],
    )
    notes: str | None = Field(
        default=None,
        description="Optional transition notes or stage synthesis from interviewer or candidate.",
    )


class StageStatusUpdate(BaseSchema):
    """Payload for updating an individual stage progress record."""

    status: StageStatusEnum = Field(
        ...,
        description="New status for the stage.",
        examples=[StageStatusEnum.IN_PROGRESS],
    )
    notes: str | None = Field(
        default=None,
        description="Updated notes or qualitative observations for this stage.",
    )
    criteria_met: list[str] = Field(
        default_factory=list,
        description="List of rubric or stage-specific criteria keys satisfied during this stage.",
    )
    stage_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary stage state data (e.g., extracted requirements, math formulas).",
    )


class StageProgressBase(BaseSchema):
    """Common attributes for session stage progress tracking."""

    stage: InterviewStage = Field(
        ...,
        description="The interview stage this progress record belongs to.",
    )
    status: StageStatusEnum = Field(
        default=StageStatusEnum.PENDING,
        description="Operational status of this stage.",
    )
    turns_spent: int = Field(
        default=0,
        description="Dialogue turns exchanged during this stage.",
    )
    duration_seconds: int = Field(
        default=0,
        description="Time spent on this stage in seconds.",
    )
    notes: str | None = Field(
        default=None,
        description="Observations or stage notes recorded by the evaluation agent.",
    )
    criteria_met: list[str] = Field(
        default_factory=list,
        description="List of checklist or rubric criteria satisfied in this stage.",
    )
    stage_state: dict[str, Any] = Field(
        default_factory=dict,
        description="Stage-specific structured state snapshot.",
    )


class StageProgressCreate(StageProgressBase):
    """Schema for initializing a stage progress record."""

    session_id: uuid.UUID = Field(
        ...,
        description="UUID of the parent interview session.",
    )


class StageProgressRead(StageProgressBase):
    """Full stage progress record returned from API queries."""

    id: uuid.UUID = Field(description="Unique stage progress record UUID.")
    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    started_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when this stage was initiated.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="UTC timestamp when this stage was marked complete or skipped.",
    )
    created_at: datetime = Field(description="Record creation timestamp.")
    updated_at: datetime = Field(description="Last record update timestamp.")


class StageStatusRead(BaseSchema):
    """Comprehensive stage status and overall progress overview for a session."""

    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    current_stage: InterviewStage = Field(description="Currently active interview stage.")
    current_stage_title: str = Field(
        description="Human-readable title of current stage.",
    )
    current_stage_description: str = Field(
        description="Guidance and expectations for current stage.",
    )
    stage_order: list[InterviewStage] = Field(
        default=INTERVIEW_STAGE_ORDER,
        description="Standard sequential progression order of interview stages.",
    )
    progress: list[StageProgressRead] = Field(
        default_factory=list,
        description="Per-stage progress and metrics records for the session.",
    )
    total_stages: int = Field(
        default=len(INTERVIEW_STAGE_ORDER),
        description="Total number of stages in the interview pipeline.",
    )
    completed_stages: int = Field(
        default=0,
        description="Number of completed or skipped stages so far.",
    )
    is_final_stage: bool = Field(
        default=False,
        description="True if currently active stage is the final evaluation stage.",
    )


class StageTransitionResponse(BaseSchema):
    """Response payload returned when a stage transition is successfully performed."""

    session_id: uuid.UUID = Field(description="Interview session UUID.")
    previous_stage: InterviewStage = Field(description="Previous active stage.")
    current_stage: InterviewStage = Field(description="New current active stage.")
    transitioned_at: datetime = Field(description="UTC timestamp of the transition.")
    message: str | None = Field(
        default=None,
        description="Descriptive status message explaining the transition.",
    )

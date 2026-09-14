"""System Design Interview Simulator - Interviewer Persona Schemas.

Defines Pydantic schemas for interviewer persona profiles, behavioral traits,
questioning styles, strictness calibrations, and customized system prompt modifiers.
"""

from enum import StrEnum
from typing import Any
import uuid
from pydantic import Field

from app.core.constants import InterviewStage, InterviewerPersona
from app.schemas import BaseSchema


class QuestioningStyleEnum(StrEnum):
    """Philosophical questioning strategy utilized by the AI interviewer."""

    SOCRATIC = "socratic"
    DIRECT = "direct"
    CHALLENGING = "challenging"
    COLLABORATIVE = "collaborative"
    DEVILS_ADVOCATE = "devils_advocate"


class PacingBiasEnum(StrEnum):
    """Tempo and time management guidance enforced by the persona."""

    FAST_PACED = "fast_paced"
    MODERATE = "moderate"
    DEEP_AND_DELIBERATE = "deep_and_deliberate"


class InterviewerPersonaTraitsSchema(BaseSchema):
    """Calibrated behavioral and stylistic dials governing the interviewer agent."""

    strictness: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Rigor applied when evaluating math, trade-offs, and edge cases (0=lenient, 1=uncompromising).",
        examples=[0.85],
    )
    encouragement_level: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Level of positive reinforcement and validation provided to candidate.",
        examples=[0.4],
    )
    hint_proactivity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Readiness to offer unprompted hints when candidate hesitates.",
        examples=[0.2],
    )
    interruption_tendency: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Tendency to interject and steer candidate away from unproductive tangents.",
        examples=[0.6],
    )
    questioning_style: QuestioningStyleEnum = Field(
        default=QuestioningStyleEnum.SOCRATIC,
        description="Primary conversational questioning methodology.",
        examples=[QuestioningStyleEnum.SOCRATIC],
    )
    pacing_bias: PacingBiasEnum = Field(
        default=PacingBiasEnum.MODERATE,
        description="Pacing tempo preference during the session.",
        examples=[PacingBiasEnum.MODERATE],
    )
    favorite_probing_topics: list[str] = Field(
        default_factory=list,
        description="Domain areas this persona prefers to drill deep into.",
        examples=[["distributed consensus", "cache stampede prevention", "database sharding keys"]],
    )


class InterviewerPersonaConfigSchema(BaseSchema):
    """Full configuration and prompt metadata for an interviewer persona."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the persona configuration.",
        examples=["persona-socratic-architect"],
    )
    persona_type: InterviewerPersona = Field(
        ...,
        description="Canonical persona identifier constant.",
        examples=[InterviewerPersona.SOCRATIC],
    )
    display_name: str = Field(
        ...,
        description="Public display name of the interviewer.",
        examples=["Dr. Sofia Socratic (Principal Architect)"],
    )
    title: str = Field(
        ...,
        description="Professional organizational title.",
        examples=["Principal Systems Architect & Infrastructure Lead"],
    )
    avatar_url: str | None = Field(
        default=None,
        description="Profile avatar or icon URL representing the persona.",
    )
    tagline: str = Field(
        ...,
        description="One-line summary of the interviewer's personality.",
        examples=["Guides candidates to discover their own system bottlenecks through deep Socratic inquiry."],
    )
    bio: str = Field(
        ...,
        description="Detailed background describing the interviewer's expertise and perspective.",
        examples=["Ex-BigTech Infrastructure Fellow specializing in highly reliable distributed storage."],
    )
    communication_style: str = Field(
        ...,
        description="Tone and language style description.",
        examples=["Calm, inquisitive, intellectually demanding, and non-prescriptive."],
    )
    traits: InterviewerPersonaTraitsSchema = Field(
        default_factory=InterviewerPersonaTraitsSchema,
        description="Behavioral dial settings for agent decision loops.",
    )
    stage_focus_prompts: dict[InterviewStage, str] = Field(
        default_factory=dict,
        description="Stage-specific prompt guidance augmenting base instructions.",
    )
    is_active: bool = Field(
        default=True,
        description="Whether this persona is available for candidate selection.",
    )


class InterviewerPersonaListRead(BaseSchema):
    """List response of available interviewer personas."""

    personas: list[InterviewerPersonaConfigSchema] = Field(
        default_factory=list,
        description="Collection of configured interviewer personas.",
    )
    total: int = Field(
        ...,
        ge=0,
        description="Total number of active personas.",
        examples=[3],
    )


class InterviewerPersonaPreferenceUpdate(BaseSchema):
    """Candidate customization options to adjust persona parameters for a session."""

    persona_type: InterviewerPersona = Field(
        ...,
        description="Selected interviewer persona.",
    )
    custom_strictness: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional custom strictness override.",
    )
    custom_hint_proactivity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional custom hint proactivity override.",
    )
    questioning_style_override: QuestioningStyleEnum | None = Field(
        default=None,
        description="Optional questioning style override.",
    )

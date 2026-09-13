"""System Design Interview Simulator - Evaluation Schemas and Scorecard DTOs.

Defines Pydantic schemas for the 5-pillar rubric evaluation, competency scoring,
hiring recommendations, and final interview debrief reports.
"""

from enum import StrEnum
import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import (
    SCORING_PILLAR_TITLES,
    ScoringPillar,
    SeniorityLevel,
)
from app.schemas import BaseSchema


class HiringRecommendationEnum(StrEnum):
    """Calibrated hiring decision recommendation."""

    STRONG_HIRE = "strong_hire"
    HIRE = "hire"
    LEAN_HIRE = "lean_hire"
    LEAN_NO_HIRE = "lean_no_hire"
    STRONG_NO_HIRE = "strong_no_hire"


class CompetencyScoreSchema(BaseSchema):
    """Detailed scoring and assessment for an individual evaluation competency pillar."""

    pillar: ScoringPillar = Field(
        ...,
        description="The specific evaluation competency pillar.",
        examples=[ScoringPillar.REQUIREMENTS_AND_CLARIFICATION],
    )
    pillar_title: str = Field(
        ...,
        description="Human-readable title of the competency pillar.",
        examples=["Requirements & Scope Clarification"],
    )
    score: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Calibrated competency score on a 1.0 to 5.0 scale.",
        examples=[4.2],
    )
    weight: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="Relative weighting contribution to the overall score.",
        examples=[0.2],
    )
    strengths: list[str] = Field(
        default_factory=list,
        description="Key strengths observed in this competency during the interview.",
        examples=["Proactively asked about read vs. write ratios and SLA requirements."],
    )
    growth_areas: list[str] = Field(
        default_factory=list,
        description="Opportunities for growth or missed edge cases in this area.",
        examples=["Did not initially account for multi-region active-active replication."],
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Specific dialogue citations or architectural artifacts supporting the score.",
    )


class EvaluationBase(BaseSchema):
    """Core attributes of an interview evaluation scorecard."""

    overall_score: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Holistic weighted aggregate score across all pillars on a 1.0 to 5.0 scale.",
        examples=[4.0],
    )
    recommended_level: SeniorityLevel = Field(
        default=SeniorityLevel.SENIOR,
        description="Recommended engineering seniority level based on performance.",
        examples=[SeniorityLevel.SENIOR],
    )
    hiring_recommendation: str = Field(
        ...,
        description="Hiring decision recommendation.",
        examples=[HiringRecommendationEnum.HIRE],
    )
    pillar_scores: dict[str, Any] = Field(
        default_factory=dict,
        description="Breakdown of competency pillar scores keyed by ScoringPillar.",
    )
    summary: str = Field(
        ...,
        description="Executive debrief summarizing performance, leadership, and technical depth.",
        examples=["Candidate demonstrated strong architectural instincts, particularly in data sharding."],
    )
    metadata_json: dict[str, Any] = Field(
        default_factory=dict,
        description="Evaluation metadata including LLM model details and calculation telemetry.",
    )


class EvaluationCreate(EvaluationBase):
    """Payload for persisting an interview evaluation scorecard."""

    session_id: uuid.UUID = Field(
        ...,
        description="UUID of the parent interview session.",
    )


class EvaluationUpdate(BaseSchema):
    """Payload for updating or refining an evaluation scorecard."""

    overall_score: float | None = Field(
        default=None,
        ge=1.0,
        le=5.0,
        description="Adjusted overall score.",
    )
    recommended_level: SeniorityLevel | None = Field(
        default=None,
        description="Adjusted seniority level.",
    )
    hiring_recommendation: str | None = Field(
        default=None,
        description="Adjusted hiring recommendation.",
    )
    pillar_scores: dict[str, Any] | None = Field(
        default=None,
        description="Adjusted pillar scores.",
    )
    summary: str | None = Field(
        default=None,
        description="Refined executive summary.",
    )
    metadata_json: dict[str, Any] | None = Field(
        default=None,
        description="Updated evaluation telemetry.",
    )


class EvaluationRead(EvaluationBase):
    """Standard evaluation scorecard returned across API queries."""

    id: uuid.UUID = Field(description="Unique evaluation record UUID.")
    session_id: uuid.UUID = Field(description="Parent interview session UUID.")
    created_at: datetime = Field(description="Scorecard creation timestamp.")
    updated_at: datetime = Field(description="Last scorecard modification timestamp.")


class EvaluationDetailRead(EvaluationRead):
    """Comprehensive evaluation debrief including parsed competency breakdown."""

    structured_pillars: list[CompetencyScoreSchema] = Field(
        default_factory=list,
        description="Normalized list of competency score breakdowns with observations.",
    )
    feedback_count: int = Field(
        default=0,
        description="Number of granular feedback and improvement tips generated.",
    )

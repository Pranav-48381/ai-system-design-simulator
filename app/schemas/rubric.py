"""System Design Interview Simulator - Rubric Schemas and DTOs.

Defines Pydantic models for evaluation rubrics, multi-pillar competency criteria,
and seniority level performance expectations.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import ScoringPillar
from app.schemas import BaseSchema


class RubricCriterionBase(BaseSchema):
    """Base definition of an individual scoring criterion."""

    pillar: ScoringPillar = Field(
        ...,
        description="Core evaluation pillar category this criterion grades.",
        examples=[ScoringPillar.REQUIREMENTS_AND_CLARIFICATION],
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Criterion title summarizing the expected capability.",
        examples=["Scope Clarification & Boundary Definition"],
    )
    description: str = Field(
        ...,
        min_length=10,
        description="Detailed description of what constitutes excellence.",
    )
    weight: float = Field(
        default=1.0,
        gt=0.0,
        description="Relative weight multiplier of this criterion in pillar calculations.",
        examples=[1.0],
    )
    level_expectations: dict[str, Any] = Field(
        default_factory=dict,
        description="Expectations mapped by seniority level (junior, mid, senior, staff, principal).",
        examples=[{
            "junior": "Asks basic functional questions when prompted.",
            "senior": "Proactively identifies edge cases, SLA requirements, and scale constraints.",
            "staff": "Frames requirements in business impact, compliance, and multi-region context.",
        }],
    )


class RubricCriterionCreate(RubricCriterionBase):
    """Schema for adding a criterion to a rubric blueprint."""

    pass


class RubricCriterionSchema(RubricCriterionBase):
    """Full representation of a persisted rubric criterion."""

    id: uuid.UUID = Field(description="Unique criterion identifier.")
    rubric_id: uuid.UUID = Field(description="Parent rubric identifier.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last modification timestamp.")


class RubricBase(BaseSchema):
    """Common attributes for evaluation rubric sets."""

    name: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Unique name identifying this evaluation rubric framework.",
        examples=["Standard Big-Tech 5-Pillar System Design Rubric"],
    )
    description: str = Field(
        ...,
        min_length=10,
        description="High-level description of grading guidelines and philosophy.",
    )
    is_default: bool = Field(
        default=False,
        description="Whether this rubric is used as the system-wide default for new sessions.",
    )


class RubricCreate(RubricBase):
    """Schema for authoring a new evaluation rubric with embedded criteria."""

    criteria: list[RubricCriterionCreate] = Field(
        default_factory=list,
        description="List of criteria to initialize with the rubric.",
    )


class RubricUpdate(BaseSchema):
    """Schema for modifying existing rubric metadata."""

    name: str | None = Field(default=None, min_length=3, max_length=128)
    description: str | None = Field(default=None, min_length=10)
    is_default: bool | None = None


class RubricRead(RubricBase):
    """Summary rubric representation without nested criteria."""

    id: uuid.UUID = Field(description="Unique rubric identifier.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last modification timestamp.")


class RubricWithCriteriaRead(RubricRead):
    """Complete rubric representation including all associated evaluation criteria."""

    criteria: list[RubricCriterionSchema] = Field(
        default_factory=list,
        description="Ordered list of rubric criteria across all 5 evaluation pillars.",
    )

"""System Design Interview Simulator - Feedback Schemas and Actionable Tips DTOs.

Defines Pydantic schemas for candidate feedback breakdown, improvement tips,
recommended learning resources, and structured interview debrief reports.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import ScoringPillar
from app.models.enums import FeedbackCategory
from app.schemas import BaseSchema

# Alias enum for schema uniformity
FeedbackCategoryEnum = FeedbackCategory


class LearningResourceSchema(BaseSchema):
    """Reference learning material or system design pattern recommendation."""

    title: str = Field(
        ...,
        max_length=255,
        description="Title of the article, paper, book chapter, or case study.",
        examples=["Designing Data-Intensive Applications: Chapter 5 - Replication"],
    )
    url: str | None = Field(
        default=None,
        description="Web URL or canonical resource link.",
        examples=["https://martin.kleppmann.com/2017/03/27/designing-data-intensive-applications.html"],
    )
    resource_type: str = Field(
        default="article",
        description="Type of material (e.g. book, paper, article, video).",
        examples=["book"],
    )
    description: str | None = Field(
        default=None,
        description="Brief guidance explaining how this resource addresses the gap.",
    )


class ImprovementTipSchema(BaseSchema):
    """Actionable improvement tip with concrete practice exercises."""

    pillar: ScoringPillar | None = Field(
        default=None,
        description="Associated evaluation competency pillar.",
        examples=[ScoringPillar.STORAGE_DATA_MODEL_AND_SCALABILITY],
    )
    category: FeedbackCategory = Field(
        default=FeedbackCategory.IMPROVEMENT,
        description="Feedback severity and classification.",
        examples=[FeedbackCategory.IMPROVEMENT],
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Concise summary headline of the recommendation.",
        examples=["Clarify Read/Write amplification before choosing LSM-Tree vs B-Tree"],
    )
    detail: str = Field(
        ...,
        description="Actionable explanation of why this distinction matters and when to apply it.",
    )
    action_items: list[str] = Field(
        default_factory=list,
        description="Practical checklist steps to practice for upcoming interviews.",
        examples=["Compare Cassandra vs Postgres storage engines under 100k write QPS."],
    )
    resources: list[LearningResourceSchema] = Field(
        default_factory=list,
        description="Hand-picked reading materials directly targeting this improvement area.",
    )


class FeedbackItemBase(BaseSchema):
    """Core attributes of an individual feedback observation item."""

    category: FeedbackCategory = Field(
        default=FeedbackCategory.IMPROVEMENT,
        description="Feedback categorization (strength, improvement, critical_gap, recommendation).",
        examples=[FeedbackCategory.STRENGTH],
    )
    pillar: ScoringPillar | None = Field(
        default=None,
        description="Applicable scoring pillar.",
        examples=[ScoringPillar.RESILIENCE_FAULT_TOLERANCE_AND_MONITORING],
    )
    title: str = Field(
        ...,
        max_length=255,
        description="Descriptive feedback headline.",
        examples=["Excellent proactive design of circuit breakers and rate limiters."],
    )
    detail: str = Field(
        ...,
        description="Comprehensive explanation with evidence from the interview dialogue.",
    )
    resources: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Associated references and study links.",
    )


class FeedbackItemCreate(FeedbackItemBase):
    """Payload for recording a feedback observation item."""

    evaluation_id: uuid.UUID = Field(
        ...,
        description="Parent interview evaluation UUID.",
    )


class FeedbackItemRead(FeedbackItemBase):
    """Complete feedback item returned from API queries."""

    id: uuid.UUID = Field(description="Unique feedback item UUID.")
    evaluation_id: uuid.UUID = Field(description="Parent evaluation UUID.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last update timestamp.")


class FeedbackReportRead(BaseSchema):
    """Aggregated debrief feedback report categorizing all observations."""

    session_id: uuid.UUID = Field(description="Interview session UUID.")
    evaluation_id: uuid.UUID = Field(description="Evaluation record UUID.")
    overall_summary: str = Field(
        description="High-level feedback summary synthesising candidate performance.",
    )
    strengths: list[FeedbackItemRead] = Field(
        default_factory=list,
        description="Validated strengths and positive engineering choices.",
    )
    improvements: list[FeedbackItemRead] = Field(
        default_factory=list,
        description="Identified growth areas and blind spots.",
    )
    critical_gaps: list[FeedbackItemRead] = Field(
        default_factory=list,
        description="Severe architectural omissions or miscalculations.",
    )
    recommendations: list[ImprovementTipSchema] = Field(
        default_factory=list,
        description="Actionable practice tips and study curriculum.",
    )
    total_items: int = Field(
        default=0,
        description="Total count of feedback observations across all categories.",
    )

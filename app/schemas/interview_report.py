"""System Design Interview Simulator - Comprehensive Interview Report DTO Schemas.

Defines Pydantic schemas for the consolidated final debrief report, aggregating
session metadata, stage execution summaries, 5-pillar rubric scorecards, artifact summaries,
strengths, risks, improvement tips, and learning resources.
"""

from enum import StrEnum
from datetime import datetime
from typing import Any
import uuid
from pydantic import Field

from app.core.constants import InterviewStage, ScoringPillar, SeniorityLevel
from app.schemas import BaseSchema
from app.schemas.evaluation import CompetencyScoreSchema, HiringRecommendationEnum
from app.schemas.feedback import ImprovementTipSchema, LearningResourceSchema


class InterviewReportExportFormatEnum(StrEnum):
    """Supported export formats for finalized interview evaluation reports."""

    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"


class InterviewStageExecutionSummarySchema(BaseSchema):
    """Summary of candidate performance and metrics within an interview stage."""

    stage: InterviewStage = Field(
        ...,
        description="The interview stage evaluated.",
        examples=[InterviewStage.REQUIREMENTS_CLARIFICATION],
    )
    stage_name: str = Field(
        ...,
        description="Human-readable title of the interview stage.",
        examples=["Requirements & Scope Clarification"],
    )
    duration_seconds: int = Field(
        default=0,
        ge=0,
        description="Total duration spent in this stage.",
        examples=[480],
    )
    turn_count: int = Field(
        default=0,
        ge=0,
        description="Number of candidate-interviewer conversational turns.",
        examples=[6],
    )
    is_completed: bool = Field(
        default=True,
        description="Whether stage exit criteria were fully satisfied.",
    )
    key_decisions: list[str] = Field(
        default_factory=list,
        description="Key architectural decisions made by candidate during this stage.",
        examples=[["Identified read-heavy traffic ratio (100:1)", "Established 99.99% availability target"]],
    )
    interviewer_observations: str | None = Field(
        default=None,
        description="Interviewer commentary on candidate communication and pacing.",
    )


class ArtifactsExecutionSummarySchema(BaseSchema):
    """High-level summary of all architectural artifacts created during the session."""

    total_artifacts: int = Field(
        default=0,
        ge=0,
        description="Total number of artifacts generated or submitted.",
    )
    has_architecture_diagram: bool = Field(
        default=False,
        description="True if candidate produced an architecture diagram.",
    )
    diagram_node_count: int = Field(
        default=0,
        ge=0,
        description="Total component nodes placed on whiteboard.",
    )
    diagram_edge_count: int = Field(
        default=0,
        ge=0,
        description="Total communication edges connecting components.",
    )
    has_capacity_estimations: bool = Field(
        default=False,
        description="True if candidate completed back-of-the-envelope calculations.",
    )
    has_api_designs: bool = Field(
        default=False,
        description="True if candidate documented API endpoint specifications.",
    )
    has_data_models: bool = Field(
        default=False,
        description="True if candidate defined schema tables and relations.",
    )


class ComprehensiveInterviewReportDTO(BaseSchema):
    """Master debrief report synthesizing the complete interview outcome."""

    report_id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        description="Unique identifier for the synthesized report.",
    )
    session_id: uuid.UUID = Field(
        ...,
        description="Associated interview session UUID.",
    )
    candidate_id: uuid.UUID = Field(
        ...,
        description="Candidate user UUID.",
    )
    candidate_name: str = Field(
        ...,
        description="Candidate full name.",
        examples=["Alex Chen"],
    )
    target_seniority: SeniorityLevel = Field(
        ...,
        description="Target engineering level calibrated against.",
        examples=[SeniorityLevel.SENIOR],
    )
    problem_id: uuid.UUID = Field(
        ...,
        description="System design problem UUID.",
    )
    problem_title: str = Field(
        ...,
        description="Title of the design problem.",
        examples=["Design a Distributed Real-Time Chat System"],
    )
    started_at: datetime = Field(
        ...,
        description="Session start timestamp.",
    )
    completed_at: datetime = Field(
        ...,
        description="Session completion timestamp.",
    )
    total_duration_seconds: int = Field(
        ...,
        ge=0,
        description="Total duration of the interview in seconds.",
        examples=[2700],
    )
    overall_score: float = Field(
        ...,
        ge=1.0,
        le=5.0,
        description="Overall weighted score on 1.0 to 5.0 scale.",
        examples=[4.1],
    )
    hiring_recommendation: HiringRecommendationEnum = Field(
        ...,
        description="Calibrated hiring recommendation.",
        examples=[HiringRecommendationEnum.HIRE],
    )
    executive_summary: str = Field(
        ...,
        description="Senior-level executive summary of candidate strengths and architectural maturity.",
        examples=["Strong candidate demonstrating deep mastery of distributed messaging and caching."],
    )
    stage_summaries: list[InterviewStageExecutionSummarySchema] = Field(
        default_factory=list,
        description="Stage-by-stage execution breakdowns.",
    )
    competency_scores: list[CompetencyScoreSchema] = Field(
        default_factory=list,
        description="5-pillar scoring breakdowns against standard industry rubrics.",
    )
    artifacts_summary: ArtifactsExecutionSummarySchema = Field(
        default_factory=ArtifactsExecutionSummarySchema,
        description="Summary of design artifacts submitted during interview.",
    )
    key_strengths: list[str] = Field(
        default_factory=list,
        description="Prominent technical strengths identified during the interview.",
        examples=[["Clear requirements scoping", "Well-reasoned database partitioning strategy"]],
    )
    identified_risks: list[str] = Field(
        default_factory=list,
        description="Architectural bottlenecks or single points of failure overlooked.",
        examples=[["Did not address cross-region replication lag for chat status indicators"]],
    )
    improvement_tips: list[ImprovementTipSchema] = Field(
        default_factory=list,
        description="Actionable, targeted improvement exercises.",
    )
    recommended_resources: list[LearningResourceSchema] = Field(
        default_factory=list,
        description="Curated learning materials addressing observed skill gaps.",
    )


class InterviewReportExportRequest(BaseSchema):
    """Request payload for generating and downloading a formatted interview report."""

    session_id: uuid.UUID = Field(
        ...,
        description="Interview session UUID to export.",
    )
    export_format: InterviewReportExportFormatEnum = Field(
        default=InterviewReportExportFormatEnum.MARKDOWN,
        description="Target file format for export.",
        examples=[InterviewReportExportFormatEnum.MARKDOWN],
    )
    include_transcript: bool = Field(
        default=True,
        description="Whether to append full conversation turn transcripts.",
    )
    include_artifacts: bool = Field(
        default=True,
        description="Whether to include diagram nodes, API contracts, and schema definitions.",
    )

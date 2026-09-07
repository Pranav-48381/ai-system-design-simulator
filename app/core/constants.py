"""System Design Interview Simulator - Core Constants.

Defines enumeration-like constants, default configurations, stage sequences,
and domain-level enumerations used across the application.
"""

from enum import StrEnum
from typing import Final


class InterviewStage(StrEnum):
    """The 6 distinct stages of a technical system design interview."""

    CLARIFICATION = "clarification"
    ESTIMATION = "estimation"
    ARCHITECTURE = "architecture"
    DEEP_DIVE = "deep_dive"
    BOTTLENECK = "bottleneck"
    EVALUATION = "evaluation"


# Sequential order of stages in a standard system design interview
INTERVIEW_STAGE_ORDER: Final[list[InterviewStage]] = [
    InterviewStage.CLARIFICATION,
    InterviewStage.ESTIMATION,
    InterviewStage.ARCHITECTURE,
    InterviewStage.DEEP_DIVE,
    InterviewStage.BOTTLENECK,
    InterviewStage.EVALUATION,
]

INTERVIEW_STAGE_TITLES: Final[dict[InterviewStage, str]] = {
    InterviewStage.CLARIFICATION: "Clarification & Requirements Definition",
    InterviewStage.ESTIMATION: "Capacity Estimation & Scale Calculations",
    InterviewStage.ARCHITECTURE: "High-Level Architecture & API Design",
    InterviewStage.DEEP_DIVE: "Component Deep Dive & Data Storage",
    InterviewStage.BOTTLENECK: "Bottlenecks, Failure Modes & Resilience",
    InterviewStage.EVALUATION: "Debrief & Comprehensive Rubric Evaluation",
}

INTERVIEW_STAGE_DESCRIPTIONS: Final[dict[InterviewStage, str]] = {
    InterviewStage.CLARIFICATION: (
        "Clarify functional and non-functional requirements, scope boundaries, "
        "and primary system constraints."
    ),
    InterviewStage.ESTIMATION: (
        "Estimate queries per second (QPS), write/read throughput, storage volume, "
        "memory cache sizes, and network bandwidth."
    ),
    InterviewStage.ARCHITECTURE: (
        "Lay out client-server interfaces, core microservices, API contracts, "
        "and end-to-end data flow."
    ),
    InterviewStage.DEEP_DIVE: (
        "Drill into critical components: database schemas, replication, partitioning, "
        "cache invalidation, and data consistency models."
    ),
    InterviewStage.BOTTLENECK: (
        "Identify single points of failure (SPOFs), traffic spikes, network partitions, "
        "rate limiting, circuit breakers, and disaster recovery."
    ),
    InterviewStage.EVALUATION: (
        "Synthesize candidate performance against the 5-pillar rubric and provide "
        "structured actionable feedback."
    ),
}


class SeniorityLevel(StrEnum):
    """Candidate seniority levels with calibrated interview expectations."""

    JUNIOR = "junior"  # L3 / SDE I
    MID = "mid"  # L4 / SDE II
    SENIOR = "senior"  # L5 / Senior SDE
    STAFF = "staff"  # L6 / Staff SDE
    PRINCIPAL = "principal"  # L7 / Principal SDE


class InterviewerPersona(StrEnum):
    """Interviewer persona styles altering tone, rigor, and probing depth."""

    COLLABORATIVE = "collaborative_senior_staff"
    RIGOROUS = "rigorous_principal"
    SOCRATIC = "socratic_architect"


class ScoringPillar(StrEnum):
    """The 5 standard competency pillars for system design evaluation."""

    REQUIREMENTS_AND_CLARIFICATION = "requirements_and_clarification"
    SYSTEM_ARCHITECTURE_AND_DATA_FLOW = "system_architecture_and_data_flow"
    STORAGE_DATA_MODEL_AND_SCALABILITY = "storage_data_model_and_scalability"
    RESILIENCE_FAULT_TOLERANCE_AND_MONITORING = (
        "resilience_fault_tolerance_and_monitoring"
    )
    COMMUNICATION_AND_TRADE_OFF_ANALYSIS = "communication_and_trade_off_analysis"


SCORING_PILLAR_TITLES: Final[dict[ScoringPillar, str]] = {
    ScoringPillar.REQUIREMENTS_AND_CLARIFICATION: "Requirements & Scope Clarification",
    ScoringPillar.SYSTEM_ARCHITECTURE_AND_DATA_FLOW: "High-Level Architecture & Data Flow",
    ScoringPillar.STORAGE_DATA_MODEL_AND_SCALABILITY: "Storage, Data Models & Scalability",
    ScoringPillar.RESILIENCE_FAULT_TOLERANCE_AND_MONITORING: "Resilience, Fault Tolerance & Recovery",
    ScoringPillar.COMMUNICATION_AND_TRADE_OFF_ANALYSIS: "Communication, Trade-offs & Justification",
}


class SpeakerRole(StrEnum):
    """Message sender roles within an interview conversation."""

    CANDIDATE = "candidate"
    INTERVIEWER = "interviewer"
    SYSTEM = "system"


class SessionStatus(StrEnum):
    """Lifecycle status of an interview session."""

    PENDING = "pending"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"


class ProblemDifficulty(StrEnum):
    """Difficulty classification for system design problems."""

    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"
    EXPERT = "expert"


class ArtifactType(StrEnum):
    """Types of architecture artifacts generated during an interview."""

    ARCHITECTURE_DIAGRAM = "architecture_diagram"
    API_SPECIFICATION = "api_specification"
    DATABASE_SCHEMA = "database_schema"
    CAPACITY_ESTIMATION = "capacity_estimation"
    CALCULATION_NOTE = "calculation_note"


class WebSocketInboundEvent(StrEnum):
    """Supported inbound event types received from candidate WebSocket clients."""

    CANDIDATE_MESSAGE = "candidate_message"
    CANVAS_UPDATE = "canvas_update"
    REQUEST_HINT = "request_hint"
    SUBMIT_STAGE = "submit_stage"
    PING = "ping"


class WebSocketOutboundEvent(StrEnum):
    """Supported outbound event types sent to candidate WebSocket clients."""

    INTERVIEWER_TOKEN = "interviewer_token"
    INTERVIEWER_MESSAGE_END = "interviewer_message_end"
    STAGE_TRANSITION = "stage_transition"
    EVALUATION_READY = "evaluation_ready"
    HINT_DELIVERED = "hint_delivered"
    ERROR = "error"
    PONG = "pong"


class LLMProvider(StrEnum):
    """Supported LLM providers for interview agent orchestration."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"

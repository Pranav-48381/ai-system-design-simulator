"""System Design Interview Simulator - Database Enum Types.

Defines SQLAlchemy-compatible PostgreSQL enum wrappers matching domain constants.
"""

import enum
from sqlalchemy import Enum

from app.core.constants import (
    ArtifactType,
    InterviewerPersona,
    InterviewStage,
    ProblemDifficulty,
    ScoringPillar,
    SeniorityLevel,
    SessionStatus,
    SpeakerRole,
)


class FeedbackCategory(enum.StrEnum):
    """Categorization of individual feedback notes given to a candidate."""

    STRENGTH = "strength"
    IMPROVEMENT = "improvement"
    CRITICAL_GAP = "critical_gap"
    RECOMMENDATION = "recommendation"


class AuditEventType(enum.StrEnum):
    """Types of tracked interview session audit events."""

    SESSION_STARTED = "session_started"
    STAGE_STARTED = "stage_started"
    STAGE_COMPLETED = "stage_completed"
    HINT_REQUESTED = "hint_requested"
    CANVAS_MODIFIED = "canvas_modified"
    SESSION_PAUSED = "session_paused"
    SESSION_RESUMED = "session_resumed"
    SESSION_COMPLETED = "session_completed"
    SESSION_ABORTED = "session_aborted"


# SQLAlchemy Enum Type Instances for Model Column Definitions
InterviewStageDBEnum = Enum(
    InterviewStage,
    name="interview_stage_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

SeniorityLevelDBEnum = Enum(
    SeniorityLevel,
    name="seniority_level_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

InterviewerPersonaDBEnum = Enum(
    InterviewerPersona,
    name="interviewer_persona_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

ScoringPillarDBEnum = Enum(
    ScoringPillar,
    name="scoring_pillar_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

SpeakerRoleDBEnum = Enum(
    SpeakerRole,
    name="speaker_role_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

SessionStatusDBEnum = Enum(
    SessionStatus,
    name="session_status_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

ProblemDifficultyDBEnum = Enum(
    ProblemDifficulty,
    name="problem_difficulty_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

ArtifactTypeDBEnum = Enum(
    ArtifactType,
    name="artifact_type_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

FeedbackCategoryDBEnum = Enum(
    FeedbackCategory,
    name="feedback_category_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

AuditEventTypeDBEnum = Enum(
    AuditEventType,
    name="audit_event_type_enum",
    create_type=True,
    values_callable=lambda obj: [e.value for e in obj],
)

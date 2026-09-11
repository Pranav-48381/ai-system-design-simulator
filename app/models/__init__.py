"""System Design Interview Simulator - Database Models Package.

Consolidates and re-exports all SQLAlchemy declarative ORM models and database enum types
for application-wide imports and Alembic schema autogeneration.
"""

from app.models.architecture_artifact import CandidateArchitectureArtifact
from app.models.audit_log import SessionAuditLog
from app.models.checkpointer import LangGraphCheckpoint, LangGraphCheckpointWrite
from app.models.enums import (
    ArtifactTypeDBEnum,
    AuditEventType,
    AuditEventTypeDBEnum,
    FeedbackCategory,
    FeedbackCategoryDBEnum,
    InterviewerPersonaDBEnum,
    InterviewStageDBEnum,
    ProblemDifficultyDBEnum,
    ScoringPillarDBEnum,
    SeniorityLevelDBEnum,
    SessionStatusDBEnum,
    SpeakerRoleDBEnum,
    UserRoleDBEnum,
)
from app.models.evaluation import InterviewEvaluation
from app.models.feedback import EvaluationFeedbackItem
from app.models.message import InterviewMessage
from app.models.problem import SystemDesignProblem
from app.models.problem_tag_association import ProblemTagAssociation
from app.models.rubric import EvaluationRubric, RubricCriterion
from app.models.session import InterviewSession
from app.models.stage_metric import StageMetric
from app.models.stage_progress import SessionStageProgress
from app.models.tag import ProblemTag
from app.models.user import User

__all__ = [
    # Enum Types & Database Wrappers
    "ArtifactTypeDBEnum",
    "AuditEventType",
    "AuditEventTypeDBEnum",
    "FeedbackCategory",
    "FeedbackCategoryDBEnum",
    "InterviewerPersonaDBEnum",
    "InterviewStageDBEnum",
    "ProblemDifficultyDBEnum",
    "ScoringPillarDBEnum",
    "SeniorityLevelDBEnum",
    "SessionStatusDBEnum",
    "SpeakerRoleDBEnum",
    "UserRoleDBEnum",
    # Core Domain Entities
    "CandidateArchitectureArtifact",
    "EvaluationFeedbackItem",
    "EvaluationRubric",
    "InterviewEvaluation",
    "InterviewMessage",
    "InterviewSession",
    "LangGraphCheckpoint",
    "LangGraphCheckpointWrite",
    "ProblemTag",
    "ProblemTagAssociation",
    "RubricCriterion",
    "SessionAuditLog",
    "SessionStageProgress",
    "StageMetric",
    "SystemDesignProblem",
    "User",
]

"""System Design Interview Simulator - Core Package.

Exposes central configuration, structured logging, domain exceptions, security
primitives, and domain constants.
"""

from app.core.config import Settings, get_settings, settings
from app.core.constants import (
    INTERVIEW_STAGE_DESCRIPTIONS,
    INTERVIEW_STAGE_ORDER,
    INTERVIEW_STAGE_TITLES,
    SCORING_PILLAR_TITLES,
    ArtifactType,
    InterviewerPersona,
    InterviewStage,
    LLMProvider,
    ProblemDifficulty,
    ScoringPillar,
    SeniorityLevel,
    SessionStatus,
    SpeakerRole,
    WebSocketInboundEvent,
    WebSocketOutboundEvent,
)
from app.core.exceptions import (
    AppException,
    AuthenticationError,
    AuthorizationError,
    DatabaseConnectionError,
    DatabaseTransactionError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    InvalidStateTransitionError,
    LLMProviderError,
    LLMResponseParsingError,
    LLMTimeoutError,
    RateLimitExceededError,
    SessionTerminatedError,
    StageLimitExceededError,
    ValidationError,
    WebSocketProtocolError,
)
from app.core.logging import (
    get_correlation_id,
    get_logger,
    get_session_id,
    set_correlation_id,
    set_session_id,
    setup_logging,
)
from app.core.security import (
    create_signed_token,
    generate_random_token,
    generate_ws_ticket,
    hash_password,
    verify_password,
    verify_signed_token,
    verify_ws_ticket,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    "settings",
    # Constants
    "ArtifactType",
    "InterviewerPersona",
    "InterviewStage",
    "INTERVIEW_STAGE_DESCRIPTIONS",
    "INTERVIEW_STAGE_ORDER",
    "INTERVIEW_STAGE_TITLES",
    "LLMProvider",
    "ProblemDifficulty",
    "ScoringPillar",
    "SCORING_PILLAR_TITLES",
    "SeniorityLevel",
    "SessionStatus",
    "SpeakerRole",
    "WebSocketInboundEvent",
    "WebSocketOutboundEvent",
    # Exceptions
    "AppException",
    "AuthenticationError",
    "AuthorizationError",
    "DatabaseConnectionError",
    "DatabaseTransactionError",
    "EntityAlreadyExistsError",
    "EntityNotFoundError",
    "InvalidStateTransitionError",
    "LLMProviderError",
    "LLMResponseParsingError",
    "LLMTimeoutError",
    "RateLimitExceededError",
    "SessionTerminatedError",
    "StageLimitExceededError",
    "ValidationError",
    "WebSocketProtocolError",
    # Logging
    "get_correlation_id",
    "get_logger",
    "get_session_id",
    "set_correlation_id",
    "set_session_id",
    "setup_logging",
    # Security
    "create_signed_token",
    "generate_random_token",
    "generate_ws_ticket",
    "hash_password",
    "verify_password",
    "verify_signed_token",
    "verify_ws_ticket",
]

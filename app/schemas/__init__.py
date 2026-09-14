"""System Design Interview Simulator - Schemas and DTOs Package.

Consolidates and re-exports all Pydantic v2 Data Transfer Objects (DTOs),
request/response validation models, and event schemas across domain entities.
"""

from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    """Foundational Pydantic v2 schema for all domain and API transfer objects.

    Configured with ORM mode enabled (from_attributes=True) for seamless conversion
    from SQLAlchemy 2.0 models, whitespace stripping on strings, and population
    by field name and alias.
    """

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
        str_strip_whitespace=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
    )


from app.schemas.api_design import (
    ApiDesignSubmissionSchema,
    ApiResponseDesignSchema,
    AuthTypeEnum,
    EndpointDesignSchema,
    HttpMethodEnum,
    ParameterLocationEnum,
    ParameterSchema,
    ProtocolTypeEnum,
    RateLimitDesignSchema,
)
from app.schemas.artifact import (
    ArtifactBase,
    ArtifactCreate,
    ArtifactListRead,
    ArtifactRead,
    ArtifactSummary,
    ArtifactTypeEnum,
    ArtifactUpdate,
)
from app.schemas.canvas import (
    DiagramEdgeSchema,
    DiagramEdgeTypeEnum,
    DiagramNodeSchema,
    DiagramNodeTypeEnum,
    WhiteboardCanvasState,
    WhiteboardSyncEvent,
)
from app.schemas.common import (
    ApiResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
)
from app.schemas.data_model_design import (
    ColumnSchemaDesign,
    DatabaseParadigmEnum,
    DataModelDesignSubmissionSchema,
    IndexSchemaDesign,
    IndexTypeEnum,
    OnDeleteActionEnum,
    PartitioningStrategySchema,
    RelationSchema,
    RelationTypeEnum,
    TableSchemaDesign,
)
from app.schemas.estimation import (
    EstimationAssumptionSchema,
    EstimationCalculationSchema,
    EstimationMetricTypeEnum,
    EstimationStageSummarySchema,
    EstimationValidationResultSchema,
    EstimationValidationStatusEnum,
    UnitOfMeasureEnum,
)
from app.schemas.evaluation import (
    CompetencyScoreSchema,
    EvaluationBase,
    EvaluationCreate,
    EvaluationDetailRead,
    EvaluationRead,
    EvaluationUpdate,
    HiringRecommendationEnum,
)
from app.schemas.feedback import (
    FeedbackCategoryEnum,
    FeedbackItemBase,
    FeedbackItemCreate,
    FeedbackItemRead,
    FeedbackReportRead,
    ImprovementTipSchema,
    LearningResourceSchema,
)
from app.schemas.interview_report import (
    ArtifactsExecutionSummarySchema,
    ComprehensiveInterviewReportDTO,
    InterviewReportExportFormatEnum,
    InterviewReportExportRequest,
    InterviewStageExecutionSummarySchema,
)
from app.schemas.problem import (
    ProblemBase,
    ProblemCreate,
    ProblemDetail,
    ProblemFilterParams,
    ProblemRead,
    ProblemSummary,
    ProblemUpdate,
    TagRead,
)
from app.schemas.rubric import (
    RubricBase,
    RubricCreate,
    RubricCriterionBase,
    RubricCriterionCreate,
    RubricCriterionSchema,
    RubricRead,
    RubricUpdate,
    RubricWithCriteriaRead,
)
from app.schemas.message import (
    CandidateTurnInput,
    MessageBase,
    MessageCreate,
    MessageFilterParams,
    MessageHistory,
    MessageRead,
)
from app.schemas.session import (
    SessionBase,
    SessionCreate,
    SessionDetailRead,
    SessionRead,
    SessionStageTransition,
    SessionStatusUpdate,
    SessionSummary,
)
from app.schemas.stage import (
    StageProgressBase,
    StageProgressCreate,
    StageProgressRead,
    StageStatusEnum,
    StageStatusRead,
    StageStatusUpdate,
    StageTransitionRequest,
    StageTransitionResponse,
)
from app.schemas.stream import (
    StreamEndEvent,
    StreamEventTypeEnum,
    StreamMetricsEvent,
    StreamStartEvent,
    TokenStreamChunk,
)
from app.schemas.user import (
    UserBase,
    UserCreate,
    UserLogin,
    UserRead,
    UserSummary,
    UserTokenResponse,
    UserUpdate,
)
from app.schemas.websocket import (
    WSCandidateMessagePayload,
    WSCanvasUpdatePayload,
    WSErrorPayload,
    WSEvaluationReadyPayload,
    WSHintDeliveredPayload,
    WSInboundMessage,
    WSInterviewerMessageEndPayload,
    WSInterviewerTokenPayload,
    WSOutboundMessage,
    WSPingPayload,
    WSPongPayload,
    WSRequestHintPayload,
    WSStageTransitionPayload,
    WSSubmitStagePayload,
    WebSocketInboundEvent,
    WebSocketOutboundEvent,
)

__all__ = [
    # API Design
    "ApiDesignSubmissionSchema",
    "ApiResponseDesignSchema",
    "AuthTypeEnum",
    "EndpointDesignSchema",
    "HttpMethodEnum",
    "ParameterLocationEnum",
    "ParameterSchema",
    "ProtocolTypeEnum",
    "RateLimitDesignSchema",
    # Artifact
    "ArtifactBase",
    "ArtifactCreate",
    "ArtifactListRead",
    "ArtifactRead",
    "ArtifactSummary",
    "ArtifactTypeEnum",
    "ArtifactUpdate",
    # Canvas
    "DiagramEdgeSchema",
    "DiagramEdgeTypeEnum",
    "DiagramNodeSchema",
    "DiagramNodeTypeEnum",
    "WhiteboardCanvasState",
    "WhiteboardSyncEvent",
    # Common
    "ApiResponse",
    "BaseSchema",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "PaginationParams",
    # Data Model Design
    "ColumnSchemaDesign",
    "DatabaseParadigmEnum",
    "DataModelDesignSubmissionSchema",
    "IndexSchemaDesign",
    "IndexTypeEnum",
    "OnDeleteActionEnum",
    "PartitioningStrategySchema",
    "RelationSchema",
    "RelationTypeEnum",
    "TableSchemaDesign",
    # Estimation
    "EstimationAssumptionSchema",
    "EstimationCalculationSchema",
    "EstimationMetricTypeEnum",
    "EstimationStageSummarySchema",
    "EstimationValidationResultSchema",
    "EstimationValidationStatusEnum",
    "UnitOfMeasureEnum",
    # Evaluation
    "CompetencyScoreSchema",
    "EvaluationBase",
    "EvaluationCreate",
    "EvaluationDetailRead",
    "EvaluationRead",
    "EvaluationUpdate",
    "HiringRecommendationEnum",
    # Feedback
    "FeedbackCategoryEnum",
    "FeedbackItemBase",
    "FeedbackItemCreate",
    "FeedbackItemRead",
    "FeedbackReportRead",
    "ImprovementTipSchema",
    "LearningResourceSchema",
    # Interview Report
    "ArtifactsExecutionSummarySchema",
    "ComprehensiveInterviewReportDTO",
    "InterviewReportExportFormatEnum",
    "InterviewReportExportRequest",
    "InterviewStageExecutionSummarySchema",
    # Message
    "CandidateTurnInput",
    "MessageBase",
    "MessageCreate",
    "MessageFilterParams",
    "MessageHistory",
    "MessageRead",
    # Problem
    "ProblemBase",
    "ProblemCreate",
    "ProblemDetail",
    "ProblemFilterParams",
    "ProblemRead",
    "ProblemSummary",
    "ProblemUpdate",
    "TagRead",
    # Rubric
    "RubricBase",
    "RubricCreate",
    "RubricCriterionBase",
    "RubricCriterionCreate",
    "RubricCriterionSchema",
    "RubricRead",
    "RubricUpdate",
    "RubricWithCriteriaRead",
    # Session
    "SessionBase",
    "SessionCreate",
    "SessionDetailRead",
    "SessionRead",
    "SessionStageTransition",
    "SessionStatusUpdate",
    "SessionSummary",
    # Stage
    "StageProgressBase",
    "StageProgressCreate",
    "StageProgressRead",
    "StageStatusEnum",
    "StageStatusRead",
    "StageStatusUpdate",
    "StageTransitionRequest",
    "StageTransitionResponse",
    # Stream
    "StreamEndEvent",
    "StreamEventTypeEnum",
    "StreamMetricsEvent",
    "StreamStartEvent",
    "TokenStreamChunk",
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserRead",
    "UserSummary",
    "UserTokenResponse",
    "UserUpdate",
    # WebSocket
    "WSCandidateMessagePayload",
    "WSCanvasUpdatePayload",
    "WSErrorPayload",
    "WSEvaluationReadyPayload",
    "WSHintDeliveredPayload",
    "WSInboundMessage",
    "WSInterviewerMessageEndPayload",
    "WSInterviewerTokenPayload",
    "WSOutboundMessage",
    "WSPingPayload",
    "WSPongPayload",
    "WSRequestHintPayload",
    "WSStageTransitionPayload",
    "WSSubmitStagePayload",
    "WebSocketInboundEvent",
    "WebSocketOutboundEvent",
]

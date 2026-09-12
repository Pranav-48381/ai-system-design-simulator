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


from app.schemas.common import (
    ApiResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
    PaginatedResponse,
    PaginationMeta,
    PaginationParams,
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
from app.schemas.session import (
    SessionBase,
    SessionCreate,
    SessionDetailRead,
    SessionRead,
    SessionStageTransition,
    SessionStatusUpdate,
    SessionSummary,
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

__all__ = [
    # Common
    "ApiResponse",
    "BaseSchema",
    "ErrorDetail",
    "ErrorResponse",
    "HealthResponse",
    "PaginatedResponse",
    "PaginationMeta",
    "PaginationParams",
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
    # User
    "UserBase",
    "UserCreate",
    "UserLogin",
    "UserRead",
    "UserSummary",
    "UserTokenResponse",
    "UserUpdate",
]

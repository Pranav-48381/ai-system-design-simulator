"""System Design Interview Simulator - Repositories Package.

Exports repository interfaces, protocols, concrete data access classes, and unit-of-work
abstractions providing asynchronous persistence operations across all domain entities.
"""

from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Protocol,
    Sequence,
    TypeVar,
    runtime_checkable,
)
import uuid

# Generic model type bound to any domain entity
ModelT = TypeVar("ModelT")
IdT = TypeVar("IdT", uuid.UUID, str, int)


@runtime_checkable
class IRepository(Protocol[ModelT, IdT]):
    """Generic repository protocol defining standard asynchronous CRUD operations."""

    async def get_by_id(self, entity_id: IdT) -> ModelT | None:
        """Fetch an entity by its primary key identifier."""
        ...

    async def get_or_raise(self, entity_id: IdT) -> ModelT:
        """Fetch an entity by ID or raise EntityNotFoundError."""
        ...

    async def list_all(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: dict[str, Any] | None = None,
    ) -> Sequence[ModelT]:
        """Fetch a paginated collection of entities matching optional filter criteria."""
        ...

    async def count(self, filters: dict[str, Any] | None = None) -> int:
        """Count total entities matching optional filter criteria."""
        ...

    async def create(self, instance: ModelT) -> ModelT:
        """Persist a new entity instance in the database."""
        ...

    async def update(self, instance: ModelT) -> ModelT:
        """Update an existing entity instance in the database."""
        ...

    async def delete(self, entity_id: IdT) -> bool:
        """Delete an entity by its identifier returning True if deleted."""
        ...


@runtime_checkable
class IUserRepository(IRepository[Any, uuid.UUID], Protocol):
    """Protocol interface for candidate and administrator user data access."""

    async def get_by_email(self, email: str) -> Any | None:
        """Retrieve user account by unique email address."""
        ...


@runtime_checkable
class IProblemRepository(IRepository[Any, uuid.UUID], Protocol):
    """Protocol interface for system design challenge catalog access."""

    async def get_by_slug(self, slug: str) -> Any | None:
        """Retrieve problem specification by unique URL slug."""
        ...


@runtime_checkable
class ISessionRepository(IRepository[Any, uuid.UUID], Protocol):
    """Protocol interface for active and completed interview sessions."""

    async def get_active_session(self, user_id: uuid.UUID) -> Any | None:
        """Retrieve the currently active interview session for a candidate."""
        ...


@runtime_checkable
class IUnitOfWork(Protocol):
    """Protocol for transactional Unit of Work managing database session lifecycle."""

    async def commit(self) -> None:
        """Commit the current transaction."""
        ...

    async def rollback(self) -> None:
        """Roll back the current transaction."""
        ...


# Safe dynamic exports for concrete implementations as they are created
_CONCRETE_EXPORTS = {
    "BaseRepository": "app.repositories.base",
    "UserRepository": "app.repositories.user_repo",
    "ProblemRepository": "app.repositories.problem_repo",
    "SessionRepository": "app.repositories.session_repo",
    "MessageRepository": "app.repositories.message_repo",
    "StageProgressRepository": "app.repositories.stage_progress_repo",
    "ArtifactRepository": "app.repositories.artifact_repo",
    "EvaluationRepository": "app.repositories.evaluation_repo",
    "FeedbackRepository": "app.repositories.feedback_repo",
    "RubricRepository": "app.repositories.rubric_repo",
    "AuditRepository": "app.repositories.audit_repo",
    "StageMetricRepository": "app.repositories.stage_metric_repo",
    "UnitOfWork": "app.repositories.unit_of_work",
}


def __getattr__(name: str) -> Any:
    """Dynamically import concrete repository classes on demand."""
    if name in _CONCRETE_EXPORTS:
        module_path = _CONCRETE_EXPORTS[name]
        try:
            module = __import__(module_path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError) as err:
            raise AttributeError(f"Repository '{name}' is not yet available in module '{module_path}': {err}") from err
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Protocols and Interfaces
    "IdT",
    "IProblemRepository",
    "IRepository",
    "ISessionRepository",
    "IUnitOfWork",
    "IUserRepository",
    "ModelT",
    # Concrete Implementations (available via __getattr__)
    "ArtifactRepository",
    "AuditRepository",
    "BaseRepository",
    "EvaluationRepository",
    "FeedbackRepository",
    "MessageRepository",
    "ProblemRepository",
    "RubricRepository",
    "SessionRepository",
    "StageMetricRepository",
    "StageProgressRepository",
    "UnitOfWork",
    "UserRepository",
]

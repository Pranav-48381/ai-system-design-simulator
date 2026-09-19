"""System Design Interview Simulator - Repository FastAPI Dependencies.

Provides dependency injection providers for FastAPI route handlers and service layers,
yielding scoped repository instances and UnitOfWork bound to the request database session.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.deps import get_db
from app.repositories.artifact_repo import ArtifactRepository
from app.repositories.audit_repo import AuditRepository
from app.repositories.evaluation_repo import EvaluationRepository
from app.repositories.feedback_repo import FeedbackRepository
from app.repositories.message_repo import MessageRepository
from app.repositories.problem_repo import ProblemRepository
from app.repositories.rubric_repo import RubricRepository
from app.repositories.session_repo import SessionRepository
from app.repositories.stage_metric_repo import StageMetricRepository
from app.repositories.stage_progress_repo import StageProgressRepository
from app.repositories.unit_of_work import UnitOfWork
from app.repositories.user_repo import UserRepository


def get_unit_of_work(session: AsyncSession = Depends(get_db)) -> UnitOfWork:
    """FastAPI dependency yielding a UnitOfWork bound to the active request session."""
    return UnitOfWork(session=session)


# Short alias for get_unit_of_work
get_uow = get_unit_of_work


def get_user_repository(session: AsyncSession = Depends(get_db)) -> UserRepository:
    """FastAPI dependency providing UserRepository instance."""
    return UserRepository(session)


def get_problem_repository(session: AsyncSession = Depends(get_db)) -> ProblemRepository:
    """FastAPI dependency providing ProblemRepository instance."""
    return ProblemRepository(session)


def get_session_repository(session: AsyncSession = Depends(get_db)) -> SessionRepository:
    """FastAPI dependency providing SessionRepository instance."""
    return SessionRepository(session)


def get_message_repository(session: AsyncSession = Depends(get_db)) -> MessageRepository:
    """FastAPI dependency providing MessageRepository instance."""
    return MessageRepository(session)


def get_stage_progress_repository(
    session: AsyncSession = Depends(get_db),
) -> StageProgressRepository:
    """FastAPI dependency providing StageProgressRepository instance."""
    return StageProgressRepository(session)


def get_artifact_repository(session: AsyncSession = Depends(get_db)) -> ArtifactRepository:
    """FastAPI dependency providing ArtifactRepository instance."""
    return ArtifactRepository(session)


def get_evaluation_repository(session: AsyncSession = Depends(get_db)) -> EvaluationRepository:
    """FastAPI dependency providing EvaluationRepository instance."""
    return EvaluationRepository(session)


def get_feedback_repository(session: AsyncSession = Depends(get_db)) -> FeedbackRepository:
    """FastAPI dependency providing FeedbackRepository instance."""
    return FeedbackRepository(session)


def get_rubric_repository(session: AsyncSession = Depends(get_db)) -> RubricRepository:
    """FastAPI dependency providing RubricRepository instance."""
    return RubricRepository(session)


def get_audit_repository(session: AsyncSession = Depends(get_db)) -> AuditRepository:
    """FastAPI dependency providing AuditRepository instance."""
    return AuditRepository(session)


def get_stage_metric_repository(
    session: AsyncSession = Depends(get_db),
) -> StageMetricRepository:
    """FastAPI dependency providing StageMetricRepository instance."""
    return StageMetricRepository(session)

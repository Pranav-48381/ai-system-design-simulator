"""System Design Interview Simulator - Asynchronous Unit of Work.

Coordinates multi-repository transactions under a single SQLAlchemy AsyncSession,
guaranteeing atomic commits, rollbacks, nested savepoints, and consistent data state
across all domain entities during complex interview orchestration steps.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any
import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.exceptions import DatabaseTransactionError
from app.core.logging import get_logger
from app.db.session import async_session_factory
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
from app.repositories.user_repo import UserRepository

logger = get_logger(__name__)


class UnitOfWork:
    """Coordinates atomic multi-repository operations over a unified asynchronous database session."""

    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        session: AsyncSession | None = None,
    ) -> None:
        """Initialize UnitOfWork with either an existing session or sessionmaker factory.

        Args:
            session_factory: Optional async sessionmaker factory. Defaults to global async_session_factory.
            session: Optional existing AsyncSession. If provided, UoW will use this session directly.
        """
        self._session_factory = session_factory or async_session_factory
        self._session = session
        self._owns_session = session is None

        # Repositories initialized when session is available
        self._users: UserRepository | None = None
        self._problems: ProblemRepository | None = None
        self._sessions: SessionRepository | None = None
        self._messages: MessageRepository | None = None
        self._stage_progress: StageProgressRepository | None = None
        self._artifacts: ArtifactRepository | None = None
        self._evaluations: EvaluationRepository | None = None
        self._feedback: FeedbackRepository | None = None
        self._rubrics: RubricRepository | None = None
        self._audit_logs: AuditRepository | None = None
        self._stage_metrics: StageMetricRepository | None = None

        if self._session is not None:
            self._init_repositories(self._session)

    def _init_repositories(self, session: AsyncSession) -> None:
        """Instantiate all concrete domain repositories bound to the active session."""
        self._users = UserRepository(session)
        self._problems = ProblemRepository(session)
        self._sessions = SessionRepository(session)
        self._messages = MessageRepository(session)
        self._stage_progress = StageProgressRepository(session)
        self._artifacts = ArtifactRepository(session)
        self._evaluations = EvaluationRepository(session)
        self._feedback = FeedbackRepository(session)
        self._rubrics = RubricRepository(session)
        self._audit_logs = AuditRepository(session)
        self._stage_metrics = StageMetricRepository(session)

    @property
    def session(self) -> AsyncSession:
        """Return the active SQLAlchemy AsyncSession or raise error if not started."""
        if self._session is None:
            raise RuntimeError("UnitOfWork session is not active. Use 'async with uow:' context manager.")
        return self._session

    @property
    def users(self) -> UserRepository:
        """Return UserRepository bound to the active session."""
        if self._users is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._users

    @property
    def problems(self) -> ProblemRepository:
        """Return ProblemRepository bound to the active session."""
        if self._problems is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._problems

    @property
    def sessions(self) -> SessionRepository:
        """Return SessionRepository bound to the active session."""
        if self._sessions is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._sessions

    @property
    def messages(self) -> MessageRepository:
        """Return MessageRepository bound to the active session."""
        if self._messages is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._messages

    @property
    def stage_progress(self) -> StageProgressRepository:
        """Return StageProgressRepository bound to the active session."""
        if self._stage_progress is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._stage_progress

    @property
    def artifacts(self) -> ArtifactRepository:
        """Return ArtifactRepository bound to the active session."""
        if self._artifacts is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._artifacts

    @property
    def evaluations(self) -> EvaluationRepository:
        """Return EvaluationRepository bound to the active session."""
        if self._evaluations is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._evaluations

    @property
    def feedback(self) -> FeedbackRepository:
        """Return FeedbackRepository bound to the active session."""
        if self._feedback is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._feedback

    @property
    def rubrics(self) -> RubricRepository:
        """Return RubricRepository bound to the active session."""
        if self._rubrics is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._rubrics

    @property
    def audit_logs(self) -> AuditRepository:
        """Return AuditRepository bound to the active session."""
        if self._audit_logs is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._audit_logs

    @property
    def stage_metrics(self) -> StageMetricRepository:
        """Return StageMetricRepository bound to the active session."""
        if self._stage_metrics is None:
            raise RuntimeError("UnitOfWork is not active.")
        return self._stage_metrics

    async def __aenter__(self) -> "UnitOfWork":
        """Enter the async context manager, creating a new session if needed."""
        if self._session is None:
            self._session = self._session_factory()
            self._init_repositories(self._session)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Exit the async context manager, rolling back on exception and closing session if owned."""
        try:
            if exc_type is not None:
                logger.warning("Rolling back UnitOfWork due to unhandled exception: %s", exc_val)
                await self.rollback()
        finally:
            if self._owns_session and self._session is not None:
                await self._session.close()
                self._session = None

    async def commit(self) -> None:
        """Commit the current database transaction.

        Raises:
            DatabaseTransactionError: If the commit fails.
        """
        try:
            await self.session.commit()
            logger.debug("Committed UnitOfWork transaction successfully.")
        except Exception as exc:
            logger.error("UnitOfWork transaction commit failed: %s", exc, exc_info=True)
            await self.rollback()
            raise DatabaseTransactionError(
                message=f"Transaction commit failed: {str(exc)}"
            ) from exc

    async def rollback(self) -> None:
        """Roll back all pending modifications in the current database transaction."""
        if self._session is not None:
            await self._session.rollback()
            logger.debug("Rolled back UnitOfWork transaction.")

    async def flush(self) -> None:
        """Flush pending changes to the database without committing the transaction."""
        await self.session.flush()

    @asynccontextmanager
    async def begin_nested(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide a savepoint nested transaction block for isolated partial failures."""
        async with self.session.begin_nested():
            try:
                yield self.session
            except Exception as exc:
                logger.warning("Nested UnitOfWork savepoint rolled back: %s", exc)
                raise

"""System Design Interview Simulator - Database Utilities & Transaction Management.

Provides explicit atomic transaction helpers and nested transaction context managers.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DatabaseTransactionError
from app.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def async_transaction(session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Provide an explicit atomic transaction block with automatic commit or rollback."""
    if session.in_transaction():
        async with session.begin_nested():
            try:
                yield session
            except Exception as exc:
                logger.error("Nested database transaction failed: %s", exc, exc_info=True)
                raise DatabaseTransactionError(
                    message=f"Nested database transaction failed: {str(exc)}"
                ) from exc
    else:
        async with session.begin():
            try:
                yield session
            except Exception as exc:
                logger.error("Database transaction failed: %s", exc, exc_info=True)
                raise DatabaseTransactionError(
                    message=f"Database transaction failed: {str(exc)}"
                ) from exc

"""System Design Interview Simulator - Database Health Check.

Provides latency measurement and liveness probing utilities for the PostgreSQL database.
"""

import time
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory


async def check_db_health(session: AsyncSession | None = None) -> dict[str, Any]:
    """Execute a lightweight probe query against PostgreSQL and calculate roundtrip latency."""
    start_time = time.perf_counter()

    async def _execute_ping(s: AsyncSession) -> None:
        result = await s.execute(text("SELECT 1;"))
        result.scalar()

    try:
        if session is not None:
            await _execute_ping(session)
        else:
            async with async_session_factory() as s:
                await _execute_ping(s)

        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "healthy",
            "database": "postgresql",
            "latency_ms": latency_ms,
            "connected": True,
        }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "status": "unhealthy",
            "database": "postgresql",
            "latency_ms": latency_ms,
            "connected": False,
            "error": str(exc),
        }

"""System Design Interview Simulator - LangGraph Checkpointer Engine.

Provides persistent and in-memory checkpoint providers for LangGraph state machine
execution, enabling session resumption, state audit traversal, and crash recovery.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone
import json
import logging
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import get_settings
from app.models.checkpointer import LangGraphCheckpoint, LangGraphCheckpointWrite

logger = logging.getLogger(__name__)


class BaseCheckpointerProvider(ABC):
    """Abstract base class for interview state checkpointers."""

    @abstractmethod
    async def get_tuple(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Retrieve the checkpoint tuple matching thread_id and optional checkpoint_id."""
        ...

    @abstractmethod
    async def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Persist a new checkpoint snapshot returning updated config."""
        ...

    @abstractmethod
    async def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        """Persist intermediate channel writes produced during node execution."""
        ...

    @abstractmethod
    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List chronological checkpoints for a given thread."""
        ...


class InMemoryCheckpointerProvider(BaseCheckpointerProvider):
    """Fast, thread-safe in-memory checkpointer provider for testing and local runs."""

    def __init__(self) -> None:
        # thread_id -> list of (checkpoint_id, checkpoint_dict, metadata_dict, parent_id)
        self._storage: dict[str, list[dict[str, Any]]] = {}
        self._writes: dict[str, list[dict[str, Any]]] = {}

    async def get_tuple(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_id = configurable.get("checkpoint_id")

        if not thread_id or thread_id not in self._storage:
            return None

        records = self._storage[thread_id]
        if not records:
            return None

        if checkpoint_id:
            for r in reversed(records):
                if r["checkpoint_id"] == checkpoint_id:
                    return r
            return None

        # Return latest checkpoint
        return records[-1]

    async def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        configurable = config.get("configurable", {})
        thread_id = str(configurable.get("thread_id", "default_thread"))
        checkpoint_id = str(checkpoint.get("id") or configurable.get("checkpoint_id") or f"chk_{len(self._storage.get(thread_id, [])) + 1}")
        parent_id = configurable.get("checkpoint_id")

        entry = {
            "thread_id": thread_id,
            "checkpoint_id": checkpoint_id,
            "parent_checkpoint_id": parent_id,
            "checkpoint": dict(checkpoint),
            "metadata": dict(metadata),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        if thread_id not in self._storage:
            self._storage[thread_id] = []
        self._storage[thread_id].append(entry)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        configurable = config.get("configurable", {})
        thread_id = str(configurable.get("thread_id", "default_thread"))
        checkpoint_id = str(configurable.get("checkpoint_id", ""))

        if thread_id not in self._writes:
            self._writes[thread_id] = []

        for idx, (channel, value) in enumerate(writes):
            self._writes[thread_id].append({
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "task_id": task_id,
                "idx": idx,
                "channel": channel,
                "value": value,
            })

    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        records = self._storage.get(thread_id, [])
        return list(reversed(records[-limit:]))


class PostgresCheckpointerProvider(BaseCheckpointerProvider):
    """PostgreSQL-backed persistent checkpointer leveraging `LangGraphCheckpoint` model."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def get_tuple(
        self,
        config: dict[str, Any],
    ) -> dict[str, Any] | None:
        configurable = config.get("configurable", {})
        thread_id = configurable.get("thread_id")
        checkpoint_id = configurable.get("checkpoint_id")

        if not thread_id:
            return None

        async with self._session_factory() as session:
            stmt = select(LangGraphCheckpoint).where(
                LangGraphCheckpoint.thread_id == str(thread_id)
            )
            if checkpoint_id:
                stmt = stmt.where(LangGraphCheckpoint.checkpoint_id == str(checkpoint_id))
            else:
                stmt = stmt.order_by(desc(LangGraphCheckpoint.created_at)).limit(1)

            result = await session.execute(stmt)
            record = result.scalars().first()
            if not record:
                return None

            return {
                "thread_id": record.thread_id,
                "checkpoint_id": record.checkpoint_id,
                "parent_checkpoint_id": record.parent_checkpoint_id,
                "checkpoint": record.checkpoint,
                "metadata": record.metadata_json,
                "created_at": record.created_at.isoformat(),
            }

    async def put(
        self,
        config: dict[str, Any],
        checkpoint: dict[str, Any],
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        configurable = config.get("configurable", {})
        thread_id = str(configurable.get("thread_id", ""))
        checkpoint_ns = str(configurable.get("checkpoint_ns", ""))
        checkpoint_id = str(
            checkpoint.get("id") or configurable.get("checkpoint_id") or f"chk_{datetime.now(timezone.utc).timestamp()}"
        )
        parent_id = configurable.get("checkpoint_id")

        async with self._session_factory() as session:
            async with session.begin():
                entity = LangGraphCheckpoint(
                    thread_id=thread_id,
                    checkpoint_ns=checkpoint_ns,
                    checkpoint_id=checkpoint_id,
                    parent_checkpoint_id=parent_id,
                    checkpoint=checkpoint,
                    metadata_json=metadata,
                )
                session.add(entity)

        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": checkpoint_id,
            }
        }

    async def put_writes(
        self,
        config: dict[str, Any],
        writes: Sequence[tuple[str, Any]],
        task_id: str,
    ) -> None:
        configurable = config.get("configurable", {})
        thread_id = str(configurable.get("thread_id", ""))
        checkpoint_ns = str(configurable.get("checkpoint_ns", ""))
        checkpoint_id = str(configurable.get("checkpoint_id", ""))

        async with self._session_factory() as session:
            async with session.begin():
                for idx, (channel, value) in enumerate(writes):
                    serialized_value = value if isinstance(value, dict) else {"val": str(value)}
                    write_entity = LangGraphCheckpointWrite(
                        thread_id=thread_id,
                        checkpoint_ns=checkpoint_ns,
                        checkpoint_id=checkpoint_id,
                        task_id=task_id,
                        idx=idx,
                        channel=channel,
                        value=serialized_value,
                    )
                    session.add(write_entity)

    async def list_checkpoints(
        self,
        thread_id: str,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            stmt = (
                select(LangGraphCheckpoint)
                .where(LangGraphCheckpoint.thread_id == str(thread_id))
                .order_by(desc(LangGraphCheckpoint.created_at))
                .limit(limit)
            )
            result = await session.execute(stmt)
            records = result.scalars().all()
            return [
                {
                    "thread_id": r.thread_id,
                    "checkpoint_id": r.checkpoint_id,
                    "parent_checkpoint_id": r.parent_checkpoint_id,
                    "checkpoint": r.checkpoint,
                    "metadata": r.metadata_json,
                    "created_at": r.created_at.isoformat(),
                }
                for r in records
            ]


# Singleton default in-memory provider
_DEFAULT_MEMORY_CHECKPOINTER = InMemoryCheckpointerProvider()


def get_checkpointer(
    provider_type: str | None = None,
    session_factory: async_sessionmaker[AsyncSession] | None = None,
) -> BaseCheckpointerProvider:
    """Factory creating or returning the configured checkpointer provider."""
    settings = get_settings()
    mode = provider_type or ("postgres" if settings.POSTGRES_DB and session_factory else "memory")

    if mode == "postgres" and session_factory:
        return PostgresCheckpointerProvider(session_factory=session_factory)

    return _DEFAULT_MEMORY_CHECKPOINTER

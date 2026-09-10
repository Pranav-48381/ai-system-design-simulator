"""System Design Interview Simulator - LangGraph Checkpoint Storage Model.

Stores execution state snapshots, graph channel values, and resumption checkpoints
for LangGraph interview workflow orchestration.
"""

from typing import Any

from sqlalchemy import Index, Integer, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class LangGraphCheckpoint(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """LangGraph execution checkpoint for conversational state persistence."""

    __tablename__ = "langgraph_checkpoints"

    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False,
    )
    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    parent_checkpoint_id: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    checkpoint: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_checkpoints_thread_ns_id",
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            unique=True,
        ),
    )


class LangGraphCheckpointWrite(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Pending or intermediate channel writes associated with a LangGraph checkpoint."""

    __tablename__ = "langgraph_checkpoint_writes"

    thread_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    checkpoint_ns: Mapped[str] = mapped_column(
        String(255),
        default="",
        nullable=False,
    )
    checkpoint_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )
    task_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    idx: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    channel: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    value: Mapped[dict[str, Any]] = mapped_column(
        JSONB().with_variant(JSON, "sqlite"),
        default=dict,
        nullable=False,
    )

    __table_args__ = (
        Index(
            "ix_checkpoint_writes_thread_ns_id_task_idx",
            "thread_id",
            "checkpoint_ns",
            "checkpoint_id",
            "task_id",
            "idx",
            unique=True,
        ),
    )

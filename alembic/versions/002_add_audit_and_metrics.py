"""Add audit logs, tags, and stage metrics.

Revision ID: 002_add_audit_and_metrics
Revises: 001_initial_schema
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "002_add_audit_and_metrics"
down_revision: str | None = "001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Reference existing enum types defined in 001_initial_schema
audit_event_type_enum = postgresql.ENUM(
    "session_started", "stage_started", "stage_completed", "hint_requested",
    "canvas_modified", "session_paused", "session_resumed", "session_completed", "session_aborted",
    name="audit_event_type_enum",
    create_type=False,
)
interview_stage_enum = postgresql.ENUM(
    "clarification", "estimation", "architecture", "deep_dive", "bottlenecks", "evaluation",
    name="interview_stage_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create tags table
    op.create_table(
        "tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(64), unique=True, index=True, nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
    )

    # 2. Create problem_tag_associations junction table
    op.create_table(
        "problem_tag_associations",
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("problems.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # 3. Create session_audit_logs table
    op.create_table(
        "session_audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("event_type", audit_event_type_enum, nullable=False, index=True),
        sa.Column("stage", interview_stage_enum, nullable=True, index=True),
        sa.Column("action", sa.String(128), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_audit_logs_session_created", "session_audit_logs", ["session_id", "created_at"])

    # 4. Create stage_metrics table
    op.create_table(
        "stage_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stage", interview_stage_enum, nullable=False, index=True),
        sa.Column("turn_count", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("duration_seconds", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("token_count_in", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("token_count_out", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("average_latency_ms", sa.Float(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_stage_metrics_session_stage", "stage_metrics", ["session_id", "stage"], unique=True)


def downgrade() -> None:
    op.drop_table("stage_metrics")
    op.drop_table("session_audit_logs")
    op.drop_table("problem_tag_associations")
    op.drop_table("tags")

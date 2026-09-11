"""Initial database schema migration for core entities.

Revision ID: 001_initial_schema
Revises: None
Create Date: 2026-09-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# PostgreSQL Enum Type Definitions
user_role_enum = postgresql.ENUM(
    "admin", "interviewer", "candidate",
    name="user_role_enum",
    create_type=False,
)
seniority_level_enum = postgresql.ENUM(
    "entry", "mid", "senior", "staff", "principal",
    name="seniority_level_enum",
    create_type=False,
)
problem_difficulty_enum = postgresql.ENUM(
    "easy", "medium", "hard",
    name="problem_difficulty_enum",
    create_type=False,
)
interview_stage_enum = postgresql.ENUM(
    "clarification", "estimation", "architecture", "deep_dive", "bottlenecks", "evaluation",
    name="interview_stage_enum",
    create_type=False,
)
interviewer_persona_enum = postgresql.ENUM(
    "collaborative", "rigorous", "socratic",
    name="interviewer_persona_enum",
    create_type=False,
)
session_status_enum = postgresql.ENUM(
    "pending", "in_progress", "paused", "completed", "aborted",
    name="session_status_enum",
    create_type=False,
)
speaker_role_enum = postgresql.ENUM(
    "system", "interviewer", "candidate",
    name="speaker_role_enum",
    create_type=False,
)
artifact_type_enum = postgresql.ENUM(
    "architecture_diagram", "database_schema", "api_definition", "calculation_notes",
    name="artifact_type_enum",
    create_type=False,
)
feedback_category_enum = postgresql.ENUM(
    "strength", "improvement", "critical_gap", "recommendation",
    name="feedback_category_enum",
    create_type=False,
)
scoring_pillar_enum = postgresql.ENUM(
    "requirements_clarification",
    "capacity_estimation",
    "architecture_design",
    "deep_dive_data_design",
    "resilience_tradeoffs",
    name="scoring_pillar_enum",
    create_type=False,
)


def upgrade() -> None:
    # 1. Create Native PostgreSQL Enum Types
    user_role_enum.create(op.get_bind(), checkfirst=True)
    seniority_level_enum.create(op.get_bind(), checkfirst=True)
    problem_difficulty_enum.create(op.get_bind(), checkfirst=True)
    interview_stage_enum.create(op.get_bind(), checkfirst=True)
    interviewer_persona_enum.create(op.get_bind(), checkfirst=True)
    session_status_enum.create(op.get_bind(), checkfirst=True)
    speaker_role_enum.create(op.get_bind(), checkfirst=True)
    artifact_type_enum.create(op.get_bind(), checkfirst=True)
    feedback_category_enum.create(op.get_bind(), checkfirst=True)
    scoring_pillar_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("email", sa.String(255), unique=True, index=True, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", user_role_enum, server_default="candidate", nullable=False),
        sa.Column("target_level", seniority_level_enum, server_default="senior", nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    # 3. Create problems table
    op.create_table(
        "problems",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("slug", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("difficulty", problem_difficulty_enum, server_default="medium", nullable=False),
        sa.Column("functional_requirements", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("non_functional_requirements", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("scale_targets", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("key_challenges", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("reference_solution", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
    )

    # 4. Create rubrics table
    op.create_table(
        "rubrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("name", sa.String(128), unique=True, index=True, nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )

    # 5. Create rubric_criteria table
    op.create_table(
        "rubric_criteria",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("rubric_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("pillar", scoring_pillar_enum, nullable=False),
        sa.Column("code", sa.String(64), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("max_points", sa.Integer(), server_default=sa.text("5"), nullable=False),
        sa.Column("weight", sa.Float(), server_default=sa.text("1.0"), nullable=False),
        sa.Column("evaluation_guide", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_rubric_criteria_rubric_code", "rubric_criteria", ["rubric_id", "code"], unique=True)

    # 6. Create interview_sessions table
    op.create_table(
        "interview_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("problem_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("problems.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("rubric_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("persona", interviewer_persona_enum, server_default="collaborative", nullable=False),
        sa.Column("target_level", seniority_level_enum, server_default="senior", nullable=False),
        sa.Column("current_stage", interview_stage_enum, server_default="clarification", nullable=False, index=True),
        sa.Column("status", session_status_enum, server_default="pending", nullable=False, index=True),
        sa.Column("total_duration_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("max_duration_seconds", sa.Integer(), server_default=sa.text("2700"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("session_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )

    # 7. Create interview_messages table
    op.create_table(
        "interview_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("role", speaker_role_enum, nullable=False),
        sa.Column("stage", interview_stage_enum, nullable=False, index=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Float(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_messages_session_seq", "interview_messages", ["session_id", "sequence_number"])

    # 8. Create stage_progress table
    op.create_table(
        "stage_progress",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("stage", interview_stage_enum, nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("turns_spent", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("criteria_met", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column("stage_state", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_stage_progress_session_stage", "stage_progress", ["session_id", "stage"], unique=True)

    # 9. Create architecture_artifacts table
    op.create_table(
        "architecture_artifacts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("artifact_type", artifact_type_enum, server_default="architecture_diagram", nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index("ix_artifacts_session_type", "architecture_artifacts", ["session_id", "artifact_type"])

    # 10. Create evaluations table
    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("interview_sessions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("recommended_level", seniority_level_enum, nullable=False),
        sa.Column("executive_summary", sa.Text(), nullable=False),
        sa.Column("pillar_scores", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("rubric_breakdown", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("evaluation_metadata", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )

    # 11. Create feedback_items table
    op.create_table(
        "feedback_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("evaluation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluations.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("category", feedback_category_enum, server_default="improvement", nullable=False),
        sa.Column("pillar", scoring_pillar_enum, nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("actionable_recommendation", sa.Text(), nullable=True),
        sa.Column("display_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
    )

    # 12. Create langgraph_checkpoints table
    op.create_table(
        "langgraph_checkpoints",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False, index=True),
        sa.Column("checkpoint_ns", sa.String(255), server_default="", nullable=False),
        sa.Column("checkpoint_id", sa.String(255), nullable=False, index=True),
        sa.Column("parent_checkpoint_id", sa.String(255), nullable=True),
        sa.Column("checkpoint", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("metadata_json", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index(
        "ix_checkpoints_thread_ns_id",
        "langgraph_checkpoints",
        ["thread_id", "checkpoint_ns", "checkpoint_id"],
        unique=True,
    )

    # 13. Create langgraph_checkpoint_writes table
    op.create_table(
        "langgraph_checkpoint_writes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Column("thread_id", sa.String(255), nullable=False, index=True),
        sa.Column("checkpoint_ns", sa.String(255), server_default="", nullable=False),
        sa.Column("checkpoint_id", sa.String(255), nullable=False, index=True),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("idx", sa.Integer(), nullable=False),
        sa.Column("channel", sa.String(255), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    )
    op.create_index(
        "ix_checkpoint_writes_thread_ns_id_task_idx",
        "langgraph_checkpoint_writes",
        ["thread_id", "checkpoint_ns", "checkpoint_id", "task_id", "idx"],
        unique=True,
    )


def downgrade() -> None:
    # Drop tables in reverse order of foreign key dependency
    op.drop_table("langgraph_checkpoint_writes")
    op.drop_table("langgraph_checkpoints")
    op.drop_table("feedback_items")
    op.drop_table("evaluations")
    op.drop_table("architecture_artifacts")
    op.drop_table("stage_progress")
    op.drop_table("interview_messages")
    op.drop_table("interview_sessions")
    op.drop_table("rubric_criteria")
    op.drop_table("rubrics")
    op.drop_table("problems")
    op.drop_table("users")

    # Drop PostgreSQL native enum types
    scoring_pillar_enum.drop(op.get_bind(), checkfirst=True)
    feedback_category_enum.drop(op.get_bind(), checkfirst=True)
    artifact_type_enum.drop(op.get_bind(), checkfirst=True)
    speaker_role_enum.drop(op.get_bind(), checkfirst=True)
    session_status_enum.drop(op.get_bind(), checkfirst=True)
    interviewer_persona_enum.drop(op.get_bind(), checkfirst=True)
    interview_stage_enum.drop(op.get_bind(), checkfirst=True)
    problem_difficulty_enum.drop(op.get_bind(), checkfirst=True)
    seniority_level_enum.drop(op.get_bind(), checkfirst=True)
    user_role_enum.drop(op.get_bind(), checkfirst=True)

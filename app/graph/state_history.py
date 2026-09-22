"""System Design Interview Simulator - LangGraph State History & Checkpoint Traversal.

Provides checkpoint tree traversal, state history reconstruction, and timeline auditing
for multi-turn system design interview executions. Enables state inspection, timeline
synthesis, stage duration calculation, and rewind analysis from LangGraph checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from app.core.constants import InterviewStage, SpeakerRole
from app.graph.checkpointer import BaseCheckpointerProvider
from app.graph.serializers import deserialize_interview_state
from app.graph.state import InterviewState

logger = logging.getLogger(__name__)


@dataclass
class CheckpointDiff:
    """Represents the semantic state delta between two chronological checkpoints."""

    prev_checkpoint_id: str | None
    curr_checkpoint_id: str
    stage_transition: tuple[str, str] | None = None
    turns_increment: int = 0
    new_messages_count: int = 0
    artifacts_changed: list[str] = field(default_factory=list)
    criteria_added: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass
class StageHistoryRecord:
    """Detailed historical execution record for a single interview stage."""

    stage: InterviewStage
    entered_at: datetime | None = None
    exited_at: datetime | None = None
    duration_seconds: float | None = None
    turn_count: int = 0
    message_count: int = 0
    candidate_message_count: int = 0
    interviewer_message_count: int = 0
    artifacts_snapshot: dict[str, Any] = field(default_factory=dict)
    criteria_satisfied: list[str] = field(default_factory=list)
    start_checkpoint_id: str | None = None
    end_checkpoint_id: str | None = None


@dataclass
class SessionTimeline:
    """Comprehensive chronological timeline of an interview session."""

    session_id: str
    total_stages_attempted: int
    total_turns: int
    total_messages: int
    stages: list[StageHistoryRecord]
    current_stage: str
    is_completed: bool
    checkpoint_count: int
    started_at: datetime | None = None
    last_active_at: datetime | None = None


def _parse_timestamp(val: Any) -> datetime | None:
    """Safely parse various datetime formats into a UTC datetime."""
    if not val:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    if isinstance(val, (int, float)):
        return datetime.fromtimestamp(val, tz=timezone.utc)
    if isinstance(val, str):
        try:
            cleaned = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(cleaned)
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            return None
    return None


def build_linear_execution_path(
    checkpoints: list[dict[str, Any]],
    target_checkpoint_id: str | None = None,
) -> list[dict[str, Any]]:
    """Traverse checkpoint parent pointers to reconstruct a linear branch.

    LangGraph checkpoints can branch or fork if rewound. This function traces
    the parent pointer chain backwards from the target leaf checkpoint to the root,
    then reverses the list to produce a forward chronological execution sequence.

    Args:
        checkpoints: Unordered or timestamp-ordered list of checkpoint records.
        target_checkpoint_id: The specific leaf checkpoint ID to trace back from.
            If omitted, the most recently created checkpoint is selected as the leaf.

    Returns:
        List of checkpoint records ordered chronologically from root to leaf.
    """
    if not checkpoints:
        return []

    by_id: dict[str, dict[str, Any]] = {}
    for c in checkpoints:
        cid = str(c.get("checkpoint_id", ""))
        if cid:
            by_id[cid] = c

    if not by_id:
        return []

    # Identify leaf checkpoint
    leaf_id = target_checkpoint_id
    if not leaf_id or leaf_id not in by_id:
        # Sort by created_at or fallback to last element
        sorted_checkpoints = sorted(
            checkpoints,
            key=lambda x: _parse_timestamp(x.get("created_at")) or datetime.min.replace(tzinfo=timezone.utc),
        )
        leaf_id = str(sorted_checkpoints[-1].get("checkpoint_id", ""))

    path: list[dict[str, Any]] = []
    curr_id: str | None = leaf_id
    visited: set[str] = set()

    while curr_id and curr_id in by_id and curr_id not in visited:
        visited.add(curr_id)
        record = by_id[curr_id]
        path.append(record)
        curr_id = record.get("parent_checkpoint_id")

    path.reverse()
    return path


def diff_checkpoints(
    prev_checkpoint: dict[str, Any] | None,
    curr_checkpoint: dict[str, Any],
) -> CheckpointDiff:
    """Compute the difference between two checkpoints in an execution path.

    Args:
        prev_checkpoint: The preceding checkpoint record, or None if root.
        curr_checkpoint: The current checkpoint record.

    Returns:
        CheckpointDiff indicating stage changes, turns, and message increments.
    """
    curr_cid = str(curr_checkpoint.get("checkpoint_id", ""))
    prev_cid = str(prev_checkpoint.get("checkpoint_id", "")) if prev_checkpoint else None

    diff = CheckpointDiff(
        prev_checkpoint_id=prev_cid,
        curr_checkpoint_id=curr_cid,
    )

    curr_state = curr_checkpoint.get("checkpoint", {}) or {}
    prev_state = prev_checkpoint.get("checkpoint", {}) or {} if prev_checkpoint else {}

    # Stage transitions
    prev_stage = str(prev_state.get("current_stage", ""))
    curr_stage = str(curr_state.get("current_stage", ""))
    if prev_stage and curr_stage and prev_stage != curr_stage:
        diff.stage_transition = (prev_stage, curr_stage)

    # Turn increments
    prev_turns = int(prev_state.get("stage_turn_count", 0) or 0)
    curr_turns = int(curr_state.get("stage_turn_count", 0) or 0)
    if curr_turns >= prev_turns:
        diff.turns_increment = curr_turns - prev_turns
    else:
        diff.turns_increment = curr_turns

    # Message counts
    prev_msgs = prev_state.get("messages", []) or []
    curr_msgs = curr_state.get("messages", []) or []
    diff.new_messages_count = max(0, len(curr_msgs) - len(prev_msgs))

    # Artifact changes
    curr_artifacts = curr_state.get("active_artifacts", {}) or {}
    prev_artifacts = prev_state.get("active_artifacts", {}) or {}
    for k, v in curr_artifacts.items():
        if k not in prev_artifacts or prev_artifacts[k] != v:
            diff.artifacts_changed.append(k)

    # Criteria changes
    curr_crit = set(curr_state.get("satisfied_criteria", []) or [])
    prev_crit = set(prev_state.get("satisfied_criteria", []) or [])
    diff.criteria_added = list(curr_crit - prev_crit)

    return diff


def reconstruct_stage_history(checkpoints: list[dict[str, Any]]) -> list[StageHistoryRecord]:
    """Reconstruct stage-by-stage progression from a linear checkpoint path.

    Args:
        checkpoints: Chronologically ordered linear branch of checkpoints.

    Returns:
        List of StageHistoryRecord describing turns, timestamps, and message counts per stage.
    """
    if not checkpoints:
        return []

    stages_history: list[StageHistoryRecord] = []
    current_record: StageHistoryRecord | None = None

    for idx, cp in enumerate(checkpoints):
        state = cp.get("checkpoint", {}) or {}
        raw_stage = state.get("current_stage")
        if not raw_stage:
            continue

        try:
            stage_enum = InterviewStage(raw_stage)
        except ValueError:
            continue

        cp_time = _parse_timestamp(cp.get("created_at")) or _parse_timestamp(
            state.get("stage_started_at")
        )
        cp_id = str(cp.get("checkpoint_id", ""))

        if current_record is None or current_record.stage != stage_enum:
            if current_record is not None:
                current_record.exited_at = cp_time
                if current_record.entered_at and current_record.exited_at:
                    current_record.duration_seconds = max(
                        0.0,
                        (current_record.exited_at - current_record.entered_at).total_seconds(),
                    )
                current_record.end_checkpoint_id = checkpoints[idx - 1].get("checkpoint_id")

            # Extract criteria and artifacts
            artifacts = dict(state.get("active_artifacts", {}) or {})
            criteria = list(state.get("satisfied_criteria", []) or [])

            current_record = StageHistoryRecord(
                stage=stage_enum,
                entered_at=cp_time,
                start_checkpoint_id=cp_id,
                artifacts_snapshot=artifacts,
                criteria_satisfied=criteria,
            )
            stages_history.append(current_record)

        # Update running metrics for the current active stage
        current_record.turn_count = max(
            current_record.turn_count,
            int(state.get("stage_turn_count", 0) or 0),
        )

        messages = state.get("messages", []) or []
        current_record.message_count = len(messages)

        cand_cnt = 0
        intv_cnt = 0
        for m in messages:
            role = ""
            if isinstance(m, dict):
                role = str(m.get("role", "")).lower()
                if not role:
                    name = str(m.get("type", "")).lower()
                    if "human" in name:
                        role = SpeakerRole.CANDIDATE.value
                    elif "ai" in name:
                        role = SpeakerRole.INTERVIEWER.value
            else:
                m_type = m.__class__.__name__.lower()
                if "human" in m_type:
                    role = SpeakerRole.CANDIDATE.value
                elif "ai" in m_type:
                    role = SpeakerRole.INTERVIEWER.value

            if role == SpeakerRole.CANDIDATE.value:
                cand_cnt += 1
            elif role == SpeakerRole.INTERVIEWER.value:
                intv_cnt += 1

        current_record.candidate_message_count = cand_cnt
        current_record.interviewer_message_count = intv_cnt
        current_record.artifacts_snapshot = dict(state.get("active_artifacts", {}) or {})
        current_record.criteria_satisfied = list(state.get("satisfied_criteria", []) or [])

    # Finalize last stage record
    if current_record and checkpoints:
        last_cp = checkpoints[-1]
        current_record.end_checkpoint_id = str(last_cp.get("checkpoint_id", ""))
        current_record.exited_at = _parse_timestamp(last_cp.get("created_at"))
        if current_record.entered_at and current_record.exited_at:
            current_record.duration_seconds = max(
                0.0,
                (current_record.exited_at - current_record.entered_at).total_seconds(),
            )

    return stages_history


class StateHistoryReconstructor:
    """Asynchronous service to inspect and reconstruct session history from checkpointer."""

    def __init__(self, checkpointer: BaseCheckpointerProvider) -> None:
        self.checkpointer = checkpointer

    async def get_linear_checkpoints(
        self,
        thread_id: str,
        limit: int = 100,
        target_checkpoint_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch and reconstruct a linear checkpoint branch for a given thread."""
        all_cps = await self.checkpointer.list_checkpoints(thread_id=thread_id, limit=limit)
        return build_linear_execution_path(all_cps, target_checkpoint_id=target_checkpoint_id)

    async def reconstruct_session_timeline(
        self,
        thread_id: str,
        limit: int = 100,
    ) -> SessionTimeline:
        """Reconstruct full interview session timeline and stage breakdown.

        Args:
            thread_id: The session thread identifier.
            limit: Maximum checkpoints to retrieve from storage.

        Returns:
            SessionTimeline with stage intervals, turn counts, and overall completion state.
        """
        all_cps = await self.checkpointer.list_checkpoints(thread_id=thread_id, limit=limit)
        linear_cps = build_linear_execution_path(all_cps)

        stage_records = reconstruct_stage_history(linear_cps)

        total_turns = sum(s.turn_count for s in stage_records)
        latest_cp = linear_cps[-1] if linear_cps else {}
        latest_state = latest_cp.get("checkpoint", {}) or {}

        curr_stage_name = str(latest_state.get("current_stage", InterviewStage.CLARIFICATION.value))
        is_completed = bool(latest_state.get("is_completed", False)) or curr_stage_name == InterviewStage.EVALUATION.value

        all_msgs = latest_state.get("messages", []) or []
        total_messages = len(all_msgs)

        started_at = None
        last_active_at = None
        if linear_cps:
            started_at = _parse_timestamp(linear_cps[0].get("created_at"))
            last_active_at = _parse_timestamp(linear_cps[-1].get("created_at"))

        return SessionTimeline(
            session_id=thread_id,
            total_stages_attempted=len(stage_records),
            total_turns=total_turns,
            total_messages=total_messages,
            stages=stage_records,
            current_stage=curr_stage_name,
            is_completed=is_completed,
            checkpoint_count=len(linear_cps),
            started_at=started_at,
            last_active_at=last_active_at,
        )

    async def inspect_state_at_checkpoint(
        self,
        thread_id: str,
        checkpoint_id: str,
    ) -> InterviewState | None:
        """Retrieve and deserialize the full typed InterviewState at a specific checkpoint.

        Args:
            thread_id: The thread identifier.
            checkpoint_id: The checkpoint ID to inspect.

        Returns:
            Typed InterviewState or None if checkpoint was not found.
        """
        record = await self.checkpointer.get_tuple(
            config={"configurable": {"thread_id": thread_id, "checkpoint_id": checkpoint_id}}
        )
        if not record:
            return None

        raw_state = record.get("checkpoint", {})
        if not raw_state:
            return None

        return deserialize_interview_state(raw_state)

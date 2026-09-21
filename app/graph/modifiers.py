"""System Design Interview Simulator - State Modifiers.

Provides functional state modifier utilities for generating partial state updates
for LangGraph nodes, managing conversation turns, stage progression, artifact
synchronization, hint tracking, calculations, and evaluation records.
"""

from collections.abc import Sequence
import time
from typing import Any

try:
    from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
except ImportError:  # pragma: no cover
    class BaseMessage:  # type: ignore[no-redef]
        """Fallback base message container when langchain_core is not installed."""

        def __init__(self, content: str = "", additional_kwargs: dict[str, Any] | None = None) -> None:
            self.content = content
            self.additional_kwargs = additional_kwargs or {}

        def __repr__(self) -> str:
            return f"{self.__class__.__name__}(content={self.content!r})"

    class HumanMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class AIMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class SystemMessage(BaseMessage):  # type: ignore[no-redef]
        pass


from app.core.constants import ArtifactType, InterviewStage, SpeakerRole
from app.graph.stages import get_next_stage
from app.graph.state import (
    InterviewState,
    append_list_reducer,
    append_messages_reducer,
    append_unique_list,
    merge_dict_list,
    merge_dict_reducer,
)


def append_turn(
    state: InterviewState | dict[str, Any],
    role: str | SpeakerRole,
    content: str,
    *,
    metadata: dict[str, Any] | None = None,
    increment_counts: bool = True,
) -> dict[str, Any]:
    """Generate a partial state update appending a dialogue message turn.

    Constructs the appropriate LangChain BaseMessage subclass based on role,
    updates turn counts, and calculates elapsed time metrics.

    Args:
        state: Current interview state dictionary.
        role: Message author role ('candidate', 'interviewer', or 'system').
        content: String message body.
        metadata: Optional dictionary of message metadata (tokens, model, latency).
        increment_counts: Whether to increment stage and total turn counters.

    Returns:
        Partial state update dictionary suitable for LangGraph node return.
    """
    role_str = role.value if isinstance(role, SpeakerRole) else str(role).lower()
    meta = dict(metadata or {})
    meta.setdefault("timestamp", time.time())
    meta.setdefault("stage", state.get("current_stage", InterviewStage.CLARIFICATION.value))

    msg: BaseMessage
    if role_str == SpeakerRole.CANDIDATE.value or role_str == "user":
        msg = HumanMessage(content=content, additional_kwargs=meta)
    elif role_str == SpeakerRole.INTERVIEWER.value or role_str == "assistant":
        msg = AIMessage(content=content, additional_kwargs=meta)
    else:
        msg = SystemMessage(content=content, additional_kwargs=meta)

    now = time.time()
    stage_start = float(state.get("stage_start_time", now))
    stage_elapsed = max(0.0, now - stage_start)

    current_stage_turns = int(state.get("stage_turn_count", 0))
    current_total_turns = int(state.get("total_turn_count", 0))

    updates: dict[str, Any] = {
        "messages": [msg],
        "stage_elapsed_seconds": stage_elapsed,
        "total_elapsed_seconds": float(state.get("total_elapsed_seconds", 0.0)) + (stage_elapsed if current_stage_turns == 0 else 0.0),
    }

    if increment_counts:
        updates["stage_turn_count"] = current_stage_turns + 1
        updates["total_turn_count"] = current_total_turns + 1

    return updates


def advance_stage(
    state: InterviewState | dict[str, Any],
    next_stage: str | InterviewStage | None = None,
) -> dict[str, Any]:
    """Generate a partial state update transitioning to the next interview stage.

    Appends the current stage to completed_stages, resets stage turn counts and
    stage start time, sets the new current_stage, and updates completion flags.

    Args:
        state: Current interview state dictionary.
        next_stage: Explicit target stage, or None to advance sequentially.

    Returns:
        Partial state update dictionary suitable for LangGraph node return.
    """
    current_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    current_stage_enum = InterviewStage(current_val)

    target_enum: InterviewStage | None
    if next_stage is not None:
        target_enum = next_stage if isinstance(next_stage, InterviewStage) else InterviewStage(str(next_stage))
    else:
        target_enum = get_next_stage(current_stage_enum)

    now = time.time()

    if target_enum is None:
        # Reached the end of all stages (Evaluation complete)
        return {
            "completed_stages": [current_stage_enum.value],
            "is_stage_complete": True,
            "is_interview_complete": True,
            "next_node": None,
        }

    return {
        "completed_stages": [current_stage_enum.value],
        "current_stage": target_enum.value,
        "stage_turn_count": 0,
        "stage_start_time": now,
        "stage_elapsed_seconds": 0.0,
        "is_stage_complete": False,
        "is_interview_complete": False,
        "candidate_intent": None,
        "next_node": None,
    }


def complete_stage(
    state: InterviewState | dict[str, Any],
    summary: str | None = None,
    satisfied_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """Generate a partial state update marking the current stage as completed.

    Args:
        state: Current interview state dictionary.
        summary: Optional synthetic summary note for the stage.
        satisfied_criteria: Optional list of rubric criteria satisfied in this stage.

    Returns:
        Partial state update dictionary.
    """
    current_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    updates: dict[str, Any] = {
        "is_stage_complete": True,
    }

    if summary:
        updates["stage_summary_notes"] = {current_val: summary}

    if satisfied_criteria:
        updates["stage_criteria_satisfied"] = {current_val: satisfied_criteria}

    return updates


def record_artifact(
    state: InterviewState | dict[str, Any],
    artifact_key: str,
    artifact_data: dict[str, Any] | str,
    artifact_type: str | ArtifactType | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate a partial state update recording or updating an architecture artifact.

    Updates active_artifacts with the latest representation and appends an entry
    to artifact_history for audit and undo/redo reconstruction.

    Args:
        state: Current interview state dictionary.
        artifact_key: Identifier key for the artifact (e.g. 'canvas', 'api_spec').
        artifact_data: Content or structured payload of the artifact.
        artifact_type: Standard artifact type categorization.
        metadata: Optional metadata (version, author, tool).

    Returns:
        Partial state update dictionary.
    """
    type_str = (
        artifact_type.value
        if isinstance(artifact_type, ArtifactType)
        else (str(artifact_type) if artifact_type else ArtifactType.ARCHITECTURE_DIAGRAM.value)
    )

    entry = {
        "key": artifact_key,
        "type": type_str,
        "data": artifact_data,
        "stage": state.get("current_stage", InterviewStage.ARCHITECTURE.value),
        "timestamp": time.time(),
        "metadata": metadata or {},
    }

    return {
        "active_artifacts": {artifact_key: artifact_data},
        "artifact_history": [entry],
    }


def record_calculation(
    state: InterviewState | dict[str, Any],
    name: str,
    expression: str,
    result: str | float | int,
    unit: str = "",
    assumptions: list[str] | None = None,
    is_validated: bool = True,
) -> dict[str, Any]:
    """Generate a partial state update recording a quantitative estimation.

    Args:
        state: Current interview state dictionary.
        name: Name of metric (e.g. 'Read QPS', 'Storage per year').
        expression: Mathematical expression or formula used.
        result: Evaluated result value.
        unit: Unit of measure (e.g. 'QPS', 'TB', 'MB/s').
        assumptions: Underlying assumptions (e.g. ['100M DAU', '10 reads per user']).
        is_validated: Whether the calculation was validated by the interviewer.

    Returns:
        Partial state update dictionary.
    """
    calc_entry = {
        "name": name,
        "expression": expression,
        "result": result,
        "unit": unit,
        "assumptions": assumptions or [],
        "is_validated": is_validated,
        "stage": state.get("current_stage", InterviewStage.ESTIMATION.value),
        "timestamp": time.time(),
    }

    return {
        "calculations": [calc_entry],
    }


def record_hint(
    state: InterviewState | dict[str, Any],
    hint_text: str,
    stage: str | InterviewStage | None = None,
    hint_tier: int = 1,
) -> dict[str, Any]:
    """Generate a partial state update recording that a hint was given.

    Increments hint_count, appends to hints_used, and clears pending_hint_request.

    Args:
        state: Current interview state dictionary.
        hint_text: Content of the hint delivered.
        stage: Stage during which hint was given.
        hint_tier: Progressive tier of hint (1=subtle nudge, 2=guidance, 3=direct hint).

    Returns:
        Partial state update dictionary.
    """
    current_stage = (
        stage.value
        if isinstance(stage, InterviewStage)
        else (str(stage) if stage else state.get("current_stage", InterviewStage.CLARIFICATION.value))
    )
    current_hints = int(state.get("hint_count", 0))

    hint_entry = {
        "hint_text": hint_text,
        "stage": current_stage,
        "tier": hint_tier,
        "timestamp": time.time(),
    }

    return {
        "hint_count": current_hints + 1,
        "hints_used": [hint_entry],
        "pending_hint_request": None,
    }


def request_hint(
    state: InterviewState | dict[str, Any],
    query: str = "",
    context: str = "",
) -> dict[str, Any]:
    """Generate a partial state update setting a pending hint request.

    Args:
        state: Current interview state dictionary.
        query: Candidate question or area of confusion.
        context: Context of the current roadblock.

    Returns:
        Partial state update dictionary.
    """
    return {
        "pending_hint_request": {
            "query": query,
            "context": context,
            "stage": state.get("current_stage", InterviewStage.CLARIFICATION.value),
            "requested_at": time.time(),
        }
    }


def record_stage_criteria(
    stage: str | InterviewStage,
    criteria: list[str] | str,
) -> dict[str, Any]:
    """Generate a partial state update adding satisfied criteria for a stage.

    Args:
        stage: Interview stage.
        criteria: Single criterion or list of criteria satisfied.

    Returns:
        Partial state update dictionary.
    """
    stage_key = stage.value if isinstance(stage, InterviewStage) else str(stage)
    items = [criteria] if isinstance(criteria, str) else list(criteria)

    return {
        "stage_criteria_satisfied": {stage_key: items},
    }


def record_stage_summary(
    stage: str | InterviewStage,
    summary_text: str,
) -> dict[str, Any]:
    """Generate a partial state update recording a stage debrief summary.

    Args:
        stage: Interview stage.
        summary_text: Summary text for the stage.

    Returns:
        Partial state update dictionary.
    """
    stage_key = stage.value if isinstance(stage, InterviewStage) else str(stage)
    return {
        "stage_summary_notes": {stage_key: summary_text},
    }


def record_evaluation(
    overall_score: float,
    hiring_recommendation: str,
    pillar_scores: dict[str, Any] | None = None,
    feedback_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Generate a partial state update finalizing the interview evaluation.

    Args:
        overall_score: Overall normalized score (1.0 to 5.0).
        hiring_recommendation: Recommendation string ('Strong No Hire', 'Leaning Hire', etc.).
        pillar_scores: Dictionary mapping ScoringPillars to numeric scores and justifications.
        feedback_items: List of granular feedback items with strengths and improvement tips.

    Returns:
        Partial state update dictionary.
    """
    updates: dict[str, Any] = {
        "overall_score": float(overall_score),
        "hiring_recommendation": hiring_recommendation,
        "is_stage_complete": True,
        "is_interview_complete": True,
    }

    if pillar_scores:
        updates["evaluations"] = pillar_scores

    if feedback_items:
        updates["feedback_items"] = feedback_items

    return updates


def set_routing(
    candidate_intent: str | None = None,
    next_node: str | None = None,
) -> dict[str, Any]:
    """Generate a partial state update setting graph routing and intent markers.

    Args:
        candidate_intent: Classified candidate intent.
        next_node: Target graph node name to route execution to.

    Returns:
        Partial state update dictionary.
    """
    updates: dict[str, Any] = {}
    if candidate_intent is not None:
        updates["candidate_intent"] = candidate_intent
    if next_node is not None:
        updates["next_node"] = next_node
    return updates


def set_error(error_message: str) -> dict[str, Any]:
    """Generate a partial state update setting an execution error message."""
    return {"error": error_message}


def clear_error() -> dict[str, Any]:
    """Generate a partial state update clearing any prior error message."""
    return {"error": None}


def apply_updates_in_place(
    state: InterviewState,
    updates: dict[str, Any],
) -> InterviewState:
    """Apply a partial state update dictionary to an InterviewState using reducers.

    Useful for testing, synchronous harnesses, and non-graph execution contexts.

    Args:
        state: State dictionary to mutate.
        updates: Partial updates to apply using respective channel reducers.

    Returns:
        The mutated state dictionary.
    """
    for key, val in updates.items():
        if key == "messages":
            state["messages"] = append_messages_reducer(state.get("messages", []), val)
        elif key == "completed_stages":
            state["completed_stages"] = append_unique_list(state.get("completed_stages", []), val)
        elif key in ("active_artifacts", "stage_summary_notes", "evaluations"):
            state[key] = merge_dict_reducer(state.get(key, {}), val)  # type: ignore[literal-required]
        elif key in ("stage_criteria_satisfied",):
            state[key] = merge_dict_list(state.get(key, {}), val)  # type: ignore[literal-required]
        elif key in ("artifact_history", "calculations", "hints_used", "feedback_items"):
            state[key] = append_list_reducer(state.get(key, []), val)  # type: ignore[literal-required]
        else:
            state[key] = val  # type: ignore[literal-required]

    return state

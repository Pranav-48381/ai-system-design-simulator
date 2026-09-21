"""System Design Interview Simulator - LangGraph State Definition.

Defines the central `InterviewState` TypedDict, channel reducer functions,
and default state initialization helpers orchestrating the multi-turn
conversational interview graph.
"""

from collections.abc import Sequence
import time
from typing import Annotated, Any, NotRequired, TypedDict

try:
    from langchain_core.messages import BaseMessage
except ImportError:  # pragma: no cover
    class BaseMessage:  # type: ignore[no-redef]
        """Fallback base message container when langchain_core is not installed."""

        def __init__(self, content: str = "", additional_kwargs: dict[str, Any] | None = None) -> None:
            self.content = content
            self.additional_kwargs = additional_kwargs or {}


from app.core.constants import (
    InterviewerPersona,
    InterviewStage,
    SeniorityLevel,
)


def append_messages_reducer(
    existing: Sequence[BaseMessage | dict[str, Any]],
    new_messages: BaseMessage | dict[str, Any] | Sequence[BaseMessage | dict[str, Any]],
) -> list[BaseMessage | dict[str, Any]]:
    """Reducer combining previous dialogue messages with new turns.

    Supports both LangChain BaseMessage objects and serialized dictionary messages,
    preserving sequence order while avoiding duplicate references.
    """
    result: list[BaseMessage | dict[str, Any]] = list(existing) if existing else []
    if not new_messages:
        return result

    incoming: list[BaseMessage | dict[str, Any]]
    if isinstance(new_messages, (list, tuple)):
        incoming = list(new_messages)
    else:
        incoming = [new_messages]

    result.extend(incoming)
    return result


def append_list_reducer(
    existing: list[Any] | None,
    new_items: Any | list[Any] | None,
) -> list[Any]:
    """Reducer appending incoming items to an existing list."""
    current = list(existing) if existing else []
    if new_items is None:
        return current
    if isinstance(new_items, list):
        current.extend(new_items)
    else:
        current.append(new_items)
    return current


def append_unique_list(
    existing: list[str] | None,
    new_items: str | list[str] | None,
) -> list[str]:
    """Reducer appending incoming items while maintaining uniqueness and insertion order."""
    seen = set(existing) if existing else set()
    result = list(existing) if existing else []
    if new_items is None:
        return result

    items = new_items if isinstance(new_items, list) else [new_items]
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def merge_dict_reducer(
    existing: dict[str, Any] | None,
    new_dict: dict[str, Any] | None,
) -> dict[str, Any]:
    """Reducer shallowly merging update dictionary into the existing dictionary."""
    result = dict(existing) if existing else {}
    if new_dict:
        result.update(new_dict)
    return result


def merge_dict_list(
    existing: dict[str, list[str]] | None,
    update: dict[str, list[str]] | None,
) -> dict[str, list[str]]:
    """Reducer merging dictionary of string lists, unioning list values per key."""
    result = {k: list(v) for k, v in (existing or {}).items()}
    if not update:
        return result

    for k, v in update.items():
        if k not in result:
            result[k] = list(v)
        else:
            existing_set = set(result[k])
            for item in v:
                if item not in existing_set:
                    existing_set.add(item)
                    result[k].append(item)
    return result


class InterviewState(TypedDict, total=False):
    """Execution state container for the LangGraph interview state machine.

    Contains candidate metadata, conversation history, stage progression,
    architecture artifacts, calculations, evaluation scores, and graph routing markers.
    """

    # -------------------------------------------------------------------------
    # Dialogue & Message Channel
    # -------------------------------------------------------------------------
    messages: Annotated[list[BaseMessage | dict[str, Any]], append_messages_reducer]

    # -------------------------------------------------------------------------
    # Session & Candidate Context
    # -------------------------------------------------------------------------
    session_id: str
    user_id: str
    candidate_name: str
    seniority_level: str
    persona: str

    # -------------------------------------------------------------------------
    # Problem Specification
    # -------------------------------------------------------------------------
    problem_id: str
    problem_slug: str
    problem_title: str
    problem_summary: str
    problem_difficulty: str
    problem_requirements: dict[str, Any]
    problem_scale: dict[str, Any]

    # -------------------------------------------------------------------------
    # Lifecycle & Stage Progress
    # -------------------------------------------------------------------------
    current_stage: str
    completed_stages: Annotated[list[str], append_unique_list]
    stage_turn_count: int
    total_turn_count: int
    stage_start_time: float
    stage_elapsed_seconds: float
    total_elapsed_seconds: float

    # -------------------------------------------------------------------------
    # Stage Criteria & Requirements Satisfaction
    # -------------------------------------------------------------------------
    stage_criteria_satisfied: Annotated[dict[str, list[str]], merge_dict_list]
    stage_summary_notes: Annotated[dict[str, str], merge_dict_reducer]

    # -------------------------------------------------------------------------
    # Whiteboard, Diagrams & Design Artifacts
    # -------------------------------------------------------------------------
    active_artifacts: Annotated[dict[str, Any], merge_dict_reducer]
    artifact_history: Annotated[list[dict[str, Any]], append_list_reducer]

    # -------------------------------------------------------------------------
    # Calculations & Quantitative Assumptions
    # -------------------------------------------------------------------------
    calculations: Annotated[list[dict[str, Any]], append_list_reducer]

    # -------------------------------------------------------------------------
    # Hints & Pedagogical Guidance
    # -------------------------------------------------------------------------
    hint_count: int
    hints_used: Annotated[list[dict[str, Any]], append_list_reducer]
    pending_hint_request: dict[str, Any] | None

    # -------------------------------------------------------------------------
    # Evaluation & Scoring Rubrics
    # -------------------------------------------------------------------------
    evaluations: Annotated[dict[str, Any], merge_dict_reducer]
    feedback_items: Annotated[list[dict[str, Any]], append_list_reducer]
    overall_score: float | None
    hiring_recommendation: str | None

    # -------------------------------------------------------------------------
    # Graph Routing, Intent & Flow Control
    # -------------------------------------------------------------------------
    candidate_intent: str | None
    next_node: str | None
    is_stage_complete: bool
    is_interview_complete: bool
    error: str | None


def create_initial_state(
    session_id: str,
    user_id: str,
    problem_slug: str,
    problem_title: str,
    problem_id: str = "",
    problem_summary: str = "",
    problem_difficulty: str = "medium",
    problem_requirements: dict[str, Any] | None = None,
    problem_scale: dict[str, Any] | None = None,
    candidate_name: str = "Candidate",
    seniority_level: str = SeniorityLevel.SENIOR.value,
    persona: str = InterviewerPersona.COLLABORATIVE.value,
    initial_stage: str = InterviewStage.CLARIFICATION.value,
) -> InterviewState:
    """Construct an initialized `InterviewState` dictionary with default values."""
    now = time.time()
    return {
        "messages": [],
        "session_id": session_id,
        "user_id": user_id,
        "candidate_name": candidate_name,
        "seniority_level": seniority_level,
        "persona": persona,
        "problem_id": problem_id,
        "problem_slug": problem_slug,
        "problem_title": problem_title,
        "problem_summary": problem_summary,
        "problem_difficulty": problem_difficulty,
        "problem_requirements": problem_requirements or {},
        "problem_scale": problem_scale or {},
        "current_stage": initial_stage,
        "completed_stages": [],
        "stage_turn_count": 0,
        "total_turn_count": 0,
        "stage_start_time": now,
        "stage_elapsed_seconds": 0.0,
        "total_elapsed_seconds": 0.0,
        "stage_criteria_satisfied": {},
        "stage_summary_notes": {},
        "active_artifacts": {},
        "artifact_history": [],
        "calculations": [],
        "hint_count": 0,
        "hints_used": [],
        "pending_hint_request": None,
        "evaluations": {},
        "feedback_items": [],
        "overall_score": None,
        "hiring_recommendation": None,
        "candidate_intent": None,
        "next_node": None,
        "is_stage_complete": False,
        "is_interview_complete": False,
        "error": None,
    }

"""System Design Interview Simulator - Interview Context Extraction Utility.

Provides strongly-typed accessors, dialogue history formatting, pacing telemetry,
and prompt variable assembly wrapping raw `InterviewState` dictionaries.
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

    class HumanMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class AIMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class SystemMessage(BaseMessage):  # type: ignore[no-redef]
        pass


from app.core.constants import InterviewStage
from app.graph.stages import (
    StageDefinition,
    get_stage_definition,
)
from app.graph.state import InterviewState


class InterviewContext:
    """Convenience wrapper around `InterviewState` providing structured accessors."""

    def __init__(self, state: InterviewState) -> None:
        self._state = state

    @property
    def raw_state(self) -> InterviewState:
        """Access underlying raw state dictionary."""
        return self._state

    # -------------------------------------------------------------------------
    # Session & Candidate Identity
    # -------------------------------------------------------------------------
    @property
    def session_id(self) -> str:
        return self._state.get("session_id", "")

    @property
    def user_id(self) -> str:
        return self._state.get("user_id", "")

    @property
    def candidate_name(self) -> str:
        return self._state.get("candidate_name", "Candidate")

    @property
    def seniority_level(self) -> str:
        return self._state.get("seniority_level", "senior")

    @property
    def persona(self) -> str:
        return self._state.get("persona", "collaborative_senior_staff")

    # -------------------------------------------------------------------------
    # Problem & Scale Specifications
    # -------------------------------------------------------------------------
    @property
    def problem_slug(self) -> str:
        return self._state.get("problem_slug", "")

    @property
    def problem_title(self) -> str:
        return self._state.get("problem_title", "")

    @property
    def problem_summary(self) -> str:
        return self._state.get("problem_summary", "")

    @property
    def problem_difficulty(self) -> str:
        return self._state.get("problem_difficulty", "medium")

    @property
    def problem_requirements(self) -> dict[str, Any]:
        return self._state.get("problem_requirements", {})

    @property
    def problem_scale(self) -> dict[str, Any]:
        return self._state.get("problem_scale", {})

    # -------------------------------------------------------------------------
    # Lifecycle & Stage Mechanics
    # -------------------------------------------------------------------------
    @property
    def current_stage(self) -> InterviewStage:
        val = self._state.get("current_stage", InterviewStage.CLARIFICATION.value)
        return InterviewStage(val)

    @property
    def stage_definition(self) -> StageDefinition:
        return get_stage_definition(self.current_stage)

    @property
    def completed_stages(self) -> list[str]:
        return list(self._state.get("completed_stages", []))

    @property
    def stage_turn_count(self) -> int:
        return self._state.get("stage_turn_count", 0)

    @property
    def total_turn_count(self) -> int:
        return self._state.get("total_turn_count", 0)

    @property
    def is_stage_complete(self) -> bool:
        return bool(self._state.get("is_stage_complete", False))

    @property
    def is_interview_complete(self) -> bool:
        return bool(self._state.get("is_interview_complete", False))

    def is_min_turns_reached(self) -> bool:
        """Check if candidate has satisfied minimum turn threshold for current stage."""
        return self.stage_turn_count >= self.stage_definition.min_turns

    def is_max_turns_exceeded(self) -> bool:
        """Check if candidate has exceeded the maximum turn threshold for current stage."""
        return self.stage_turn_count >= self.stage_definition.max_turns

    # -------------------------------------------------------------------------
    # Pacing & Timing
    # -------------------------------------------------------------------------
    def get_stage_elapsed_seconds(self) -> float:
        start = self._state.get("stage_start_time")
        if start:
            return max(0.0, time.time() - start)
        return float(self._state.get("stage_elapsed_seconds", 0.0))

    def get_stage_allocated_seconds(self) -> float:
        return float(self.stage_definition.target_duration_minutes * 60)

    def get_stage_remaining_seconds(self) -> float:
        return max(0.0, self.get_stage_allocated_seconds() - self.get_stage_elapsed_seconds())

    # -------------------------------------------------------------------------
    # Dialogue & Conversation Extraction
    # -------------------------------------------------------------------------
    @property
    def messages(self) -> Sequence[BaseMessage | dict[str, Any]]:
        return self._state.get("messages", [])

    def format_recent_dialogue(self, max_turns: int = 10) -> list[dict[str, str]]:
        """Extract and format recent dialogue turns into standard role/content dicts."""
        formatted: list[dict[str, str]] = []
        recent = self.messages[-max_turns:] if max_turns > 0 else self.messages

        for msg in recent:
            if isinstance(msg, BaseMessage):
                role = "candidate" if isinstance(msg, HumanMessage) else "interviewer"
                if isinstance(msg, SystemMessage):
                    role = "system"
                formatted.append({"role": role, "content": str(msg.content)})
            elif isinstance(msg, dict):
                role = str(msg.get("role", "interviewer"))
                content = str(msg.get("content", ""))
                formatted.append({"role": role, "content": content})

        return formatted

    def get_latest_candidate_text(self) -> str:
        """Return text content of the most recent candidate message."""
        for msg in reversed(self.messages):
            if isinstance(msg, HumanMessage):
                return str(msg.content)
            if isinstance(msg, dict) and msg.get("role") == "candidate":
                return str(msg.get("content", ""))
        return ""

    def get_latest_interviewer_text(self) -> str:
        """Return text content of the most recent interviewer response."""
        for msg in reversed(self.messages):
            if isinstance(msg, AIMessage):
                return str(msg.content)
            if isinstance(msg, dict) and msg.get("role") == "interviewer":
                return str(msg.get("content", ""))
        return ""

    # -------------------------------------------------------------------------
    # Whiteboard, Canvas & Calculations
    # -------------------------------------------------------------------------
    def get_active_diagram(self) -> str | None:
        """Retrieve latest candidate architecture diagram content (e.g. Mermaid or text)."""
        artifacts = self._state.get("active_artifacts", {})
        diag = artifacts.get("architecture_diagram") or artifacts.get("canvas")
        if isinstance(diag, dict):
            return diag.get("content")
        if isinstance(diag, str):
            return diag
        return None

    def get_calculations(self) -> list[dict[str, Any]]:
        return list(self._state.get("calculations", []))

    # -------------------------------------------------------------------------
    # Criteria & Progress Satisfaction
    # -------------------------------------------------------------------------
    def get_satisfied_criteria(self, stage: InterviewStage | None = None) -> list[str]:
        target = (stage or self.current_stage).value
        mapping = self._state.get("stage_criteria_satisfied", {})
        return list(mapping.get(target, []))

    # -------------------------------------------------------------------------
    # Prompt Variable Assembly
    # -------------------------------------------------------------------------
    def to_prompt_context(self) -> dict[str, Any]:
        """Bundle context variables ready for insertion into LLM prompt templates."""
        return {
            "candidate_name": self.candidate_name,
            "seniority_level": self.seniority_level,
            "persona": self.persona,
            "problem_title": self.problem_title,
            "problem_slug": self.problem_slug,
            "problem_summary": self.problem_summary,
            "problem_difficulty": self.problem_difficulty,
            "problem_requirements": self.problem_requirements,
            "problem_scale": self.problem_scale,
            "current_stage": self.current_stage.value,
            "stage_title": self.stage_definition.title,
            "stage_turn_count": self.stage_turn_count,
            "satisfied_criteria": self.get_satisfied_criteria(),
            "active_diagram": self.get_active_diagram() or "None provided yet",
            "calculations": self.get_calculations(),
            "elapsed_minutes": round(self.get_stage_elapsed_seconds() / 60.0, 1),
            "target_minutes": self.stage_definition.target_duration_minutes,
        }

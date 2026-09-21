"""System Design Interview Simulator - LangGraph Internal Types & Containers.

Defines candidate intent classification schemas, graph action enums, node execution
result containers, routing decision types, and node name constants orchestrating
the LangGraph interview state machine.
"""

from dataclasses import dataclass, field
from enum import StrEnum
import time
from typing import Any, TypedDict

from app.core.constants import InterviewStage, SpeakerRole


class CandidateAction(StrEnum):
    """Categorization of candidate input intent within an interview turn."""

    RESPOND = "respond"
    ASK_QUESTION = "ask_question"
    SUBMIT_ESTIMATION = "submit_estimation"
    UPDATE_CANVAS = "update_canvas"
    REQUEST_HINT = "request_hint"
    SUBMIT_STAGE = "submit_stage"
    CONCUR_OR_MODIFY = "concur_or_modify"
    SKIP_STAGE = "skip_stage"
    GENERAL_QUERY = "general_query"


class GraphNodeName(StrEnum):
    """Canonical identifier names for nodes in the LangGraph StateGraph."""

    ROUTER = "router"
    CLARIFICATION = "clarification"
    ESTIMATION = "estimation"
    ARCHITECTURE = "architecture"
    DEEP_DIVE = "deep_dive"
    BOTTLENECK = "bottleneck"
    INTERVIEWER = "interviewer"
    HINT_GENERATOR = "hint_generator"
    STAGE_EVALUATOR = "stage_evaluator"
    FINAL_EVALUATOR = "final_evaluator"
    REPORT_GENERATOR = "report_generator"
    TIMEOUT = "timeout"
    ERROR_FALLBACK = "error_fallback"


@dataclass
class CandidateIntentClassification:
    """Structured extraction of candidate intent from dialogue or WebSocket event."""

    action: CandidateAction
    confidence: float = 1.0
    target_stage: InterviewStage | None = None
    extracted_entities: dict[str, Any] = field(default_factory=dict)
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action.value,
            "confidence": self.confidence,
            "target_stage": self.target_stage.value if self.target_stage else None,
            "extracted_entities": self.extracted_entities,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
        }


@dataclass
class TokenUsage:
    """LLM token consumption metrics for a graph node invocation."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass
class NodeResult:
    """Execution output container returned by LangGraph node implementations."""

    node_name: str
    updates: dict[str, Any] = field(default_factory=dict)
    next_node: str | None = None
    events: list[Any] = field(default_factory=list)
    latency_ms: float = 0.0
    token_usage: TokenUsage = field(default_factory=TokenUsage)
    is_success: bool = True
    error: str | None = None

    def to_state_update(self) -> dict[str, Any]:
        """Convert result into standard state update dictionary with next_node marker."""
        res = dict(self.updates)
        if self.next_node is not None:
            res["next_node"] = self.next_node
        if self.error is not None:
            res["error"] = self.error
        return res


@dataclass
class StageTransitionDecision:
    """Routing evaluation determining whether to advance stages."""

    can_transition: bool
    from_stage: InterviewStage
    to_stage: InterviewStage | None
    reason: str
    missing_criteria: list[str] = field(default_factory=list)
    recommended_action: str = "continue"

    def to_dict(self) -> dict[str, Any]:
        return {
            "can_transition": self.can_transition,
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value if self.to_stage else None,
            "reason": self.reason,
            "missing_criteria": self.missing_criteria,
            "recommended_action": self.recommended_action,
        }


# -----------------------------------------------------------------------------
# Specialized TypedDicts for Node Return Signatures
# -----------------------------------------------------------------------------

class RouterNodeOutput(TypedDict, total=False):
    """Output shape returned by router_node."""
    candidate_intent: str
    next_node: str
    stage_criteria_satisfied: dict[str, list[str]]
    error: str | None


class ClarificationNodeOutput(TypedDict, total=False):
    """Output shape returned by clarification_node."""
    messages: list[Any]
    stage_turn_count: int
    total_turn_count: int
    stage_criteria_satisfied: dict[str, list[str]]
    stage_summary_notes: dict[str, str]
    next_node: str | None


class EstimationNodeOutput(TypedDict, total=False):
    """Output shape returned by estimation_node."""
    messages: list[Any]
    calculations: list[dict[str, Any]]
    stage_turn_count: int
    total_turn_count: int
    stage_criteria_satisfied: dict[str, list[str]]
    next_node: str | None


class ArchitectureNodeOutput(TypedDict, total=False):
    """Output shape returned by architecture_node."""
    messages: list[Any]
    active_artifacts: dict[str, Any]
    artifact_history: list[dict[str, Any]]
    stage_turn_count: int
    total_turn_count: int
    stage_criteria_satisfied: dict[str, list[str]]
    next_node: str | None


class DeepDiveNodeOutput(TypedDict, total=False):
    """Output shape returned by deep_dive_node."""
    messages: list[Any]
    stage_turn_count: int
    total_turn_count: int
    stage_criteria_satisfied: dict[str, list[str]]
    next_node: str | None


class BottleneckNodeOutput(TypedDict, total=False):
    """Output shape returned by bottleneck_node."""
    messages: list[Any]
    stage_turn_count: int
    total_turn_count: int
    stage_criteria_satisfied: dict[str, list[str]]
    next_node: str | None


class EvaluationNodeOutput(TypedDict, total=False):
    """Output shape returned by final_evaluator_node."""
    evaluations: dict[str, Any]
    feedback_items: list[dict[str, Any]]
    overall_score: float
    hiring_recommendation: str
    is_stage_complete: bool
    is_interview_complete: bool
    next_node: str | None

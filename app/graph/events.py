"""System Design Interview Simulator - Graph Execution Event Definitions.

Defines internal graph execution telemetry and streaming event containers,
plus translation converters bridging LangGraph node outputs to client WebSocket frames.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
import time
from typing import Any
import uuid

from app.core.constants import (
    InterviewStage,
    WebSocketOutboundEvent,
)


class GraphEventType(StrEnum):
    """Event classifications emitted during LangGraph interview workflow execution."""

    NODE_START = "node_start"
    NODE_COMPLETE = "node_complete"
    TOKEN_STREAM = "token_stream"
    MESSAGE_END = "message_end"
    STAGE_TRANSITION = "stage_transition"
    HINT_DELIVERED = "hint_delivered"
    EVALUATION_READY = "evaluation_ready"
    ERROR = "error"
    STATE_SNAPSHOT = "state_snapshot"


@dataclass
class GraphEvent:
    """Base event container dispatched by LangGraph nodes and execution listeners."""

    event_type: GraphEventType
    session_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to a plain dictionary."""
        return {
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "payload": self.payload,
            "timestamp": self.timestamp,
        }


@dataclass
class TokenStreamEvent(GraphEvent):
    """Emitted when an LLM inference turn produces a token chunk."""

    def __init__(
        self,
        session_id: str,
        token: str,
        index: int,
        stage: str | InterviewStage,
        message_id: str | None = None,
    ) -> None:
        stage_val = stage.value if isinstance(stage, InterviewStage) else stage
        super().__init__(
            event_type=GraphEventType.TOKEN_STREAM,
            session_id=session_id,
            payload={
                "token": token,
                "index": index,
                "stage": stage_val,
                "message_id": message_id,
            },
        )


@dataclass
class MessageEndEvent(GraphEvent):
    """Emitted when an interviewer speaking turn completes."""

    def __init__(
        self,
        session_id: str,
        message_id: str,
        full_content: str,
        stage: str | InterviewStage,
        token_count: int = 0,
        suggested_next_action: str | None = None,
    ) -> None:
        stage_val = stage.value if isinstance(stage, InterviewStage) else stage
        super().__init__(
            event_type=GraphEventType.MESSAGE_END,
            session_id=session_id,
            payload={
                "message_id": message_id,
                "full_content": full_content,
                "stage": stage_val,
                "token_count": token_count,
                "suggested_next_action": suggested_next_action,
            },
        )


@dataclass
class StageTransitionEvent(GraphEvent):
    """Emitted when the interview progresses to a new lifecycle stage."""

    def __init__(
        self,
        session_id: str,
        previous_stage: str | InterviewStage,
        current_stage: str | InterviewStage,
        stage_title: str,
        stage_description: str,
    ) -> None:
        prev_val = previous_stage.value if isinstance(previous_stage, InterviewStage) else previous_stage
        curr_val = current_stage.value if isinstance(current_stage, InterviewStage) else current_stage
        super().__init__(
            event_type=GraphEventType.STAGE_TRANSITION,
            session_id=session_id,
            payload={
                "session_id": session_id,
                "previous_stage": prev_val,
                "current_stage": curr_val,
                "stage_title": stage_title,
                "stage_description": stage_description,
                "transitioned_at": datetime.now(timezone.utc).isoformat(),
            },
        )


@dataclass
class HintDeliveredEvent(GraphEvent):
    """Emitted when unblocking hint guidance is synthesized for a candidate."""

    def __init__(
        self,
        session_id: str,
        stage: str | InterviewStage,
        hint_text: str,
        tier: int,
        hints_remaining: int = 0,
    ) -> None:
        stage_val = stage.value if isinstance(stage, InterviewStage) else stage
        super().__init__(
            event_type=GraphEventType.HINT_DELIVERED,
            session_id=session_id,
            payload={
                "stage": stage_val,
                "hint_text": hint_text,
                "tier": tier,
                "hints_remaining": hints_remaining,
            },
        )


@dataclass
class EvaluationReadyEvent(GraphEvent):
    """Emitted when the final multi-pillar scorecard synthesis concludes."""

    def __init__(
        self,
        session_id: str,
        evaluation_id: str,
        overall_score: float,
        hiring_recommendation: str,
        summary: str,
    ) -> None:
        super().__init__(
            event_type=GraphEventType.EVALUATION_READY,
            session_id=session_id,
            payload={
                "session_id": session_id,
                "evaluation_id": evaluation_id,
                "overall_score": overall_score,
                "hiring_recommendation": hiring_recommendation,
                "summary": summary,
            },
        )


@dataclass
class GraphErrorEvent(GraphEvent):
    """Emitted when an unhandled node failure or timeout occurs."""

    def __init__(
        self,
        session_id: str,
        code: str,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(
            event_type=GraphEventType.ERROR,
            session_id=session_id,
            payload={
                "code": code,
                "message": message,
                "detail": detail or {},
            },
        )


# Mapping from internal GraphEventType to external WebSocketOutboundEvent
_GRAPH_TO_WS_MAP: dict[GraphEventType, WebSocketOutboundEvent | None] = {
    GraphEventType.TOKEN_STREAM: WebSocketOutboundEvent.INTERVIEWER_TOKEN,
    GraphEventType.MESSAGE_END: WebSocketOutboundEvent.INTERVIEWER_MESSAGE_END,
    GraphEventType.STAGE_TRANSITION: WebSocketOutboundEvent.STAGE_TRANSITION,
    GraphEventType.HINT_DELIVERED: WebSocketOutboundEvent.HINT_DELIVERED,
    GraphEventType.EVALUATION_READY: WebSocketOutboundEvent.EVALUATION_READY,
    GraphEventType.ERROR: WebSocketOutboundEvent.ERROR,
    GraphEventType.NODE_START: None,  # Internal telemetry only
    GraphEventType.NODE_COMPLETE: None,  # Internal telemetry only
    GraphEventType.STATE_SNAPSHOT: None,  # Internal telemetry only
}


def to_websocket_message(event: GraphEvent) -> dict[str, Any] | None:
    """Convert an internal `GraphEvent` into an outbound WebSocket frame dictionary.

    Returns None if the event is strictly internal telemetry.
    """
    ws_event = _GRAPH_TO_WS_MAP.get(event.event_type)
    if ws_event is None:
        return None

    return {
        "event": ws_event.value,
        "session_id": event.session_id,
        "payload": event.payload,
        "timestamp": datetime.fromtimestamp(event.timestamp, tz=timezone.utc).isoformat(),
    }

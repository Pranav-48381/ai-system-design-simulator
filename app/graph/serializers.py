"""System Design Interview Simulator - LangGraph State Serializers.

Provides robust bi-directional serialization and deserialization helpers converting
rich `InterviewState` structures, LangChain messages, enums, and timestamps into
JSON-safe payloads for PostgreSQL checkpoint persistence and WebSocket streaming.
"""

from collections.abc import Sequence
from datetime import date, datetime
from enum import Enum
import json
import time
from typing import Any
from uuid import UUID

try:
    from langchain_core.messages import (
        AIMessage,
        BaseMessage,
        ChatMessage,
        HumanMessage,
        SystemMessage,
    )
except ImportError:  # pragma: no cover
    class BaseMessage:  # type: ignore[no-redef]
        """Fallback base message container when langchain_core is not installed."""

        def __init__(
            self,
            content: str = "",
            additional_kwargs: dict[str, Any] | None = None,
            id: str | None = None,
            name: str | None = None,
        ) -> None:
            self.content = content
            self.additional_kwargs = additional_kwargs or {}
            self.id = id
            self.name = name

    class HumanMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class AIMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class SystemMessage(BaseMessage):  # type: ignore[no-redef]
        pass

    class ChatMessage(BaseMessage):  # type: ignore[no-redef]
        def __init__(self, role: str = "", content: str = "", **kwargs: Any) -> None:
            super().__init__(content=content, **kwargs)
            self.role = role

from app.core.constants import InterviewStage, SpeakerRole
from app.graph.state import InterviewState, create_initial_state


class StateJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder handling UUIDs, datetimes, enums, and LangChain messages."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, BaseMessage):
            return serialize_message(obj)
        if hasattr(obj, "to_dict") and callable(obj.to_dict):
            return obj.to_dict()
        return super().default(obj)


def serialize_message(msg: BaseMessage | dict[str, Any]) -> dict[str, Any]:
    """Serialize a LangChain BaseMessage or message dictionary into a JSON-safe dict.

    Args:
        msg: LangChain message instance or dictionary.

    Returns:
        JSON-compliant dictionary containing role, content, additional_kwargs, id, and name.
    """
    if isinstance(msg, dict):
        role = str(msg.get("role", SpeakerRole.INTERVIEWER.value)).lower()
        return {
            "type": "message",
            "role": role,
            "content": str(msg.get("content", "")),
            "additional_kwargs": dict(msg.get("additional_kwargs", {})),
            "id": msg.get("id"),
            "name": msg.get("name"),
        }

    role = SpeakerRole.INTERVIEWER.value
    msg_type = "ai"
    cls_name = msg.__class__.__name__

    if isinstance(msg, HumanMessage) or cls_name == "HumanMessage":
        role = SpeakerRole.CANDIDATE.value
        msg_type = "human"
    elif isinstance(msg, SystemMessage) or cls_name == "SystemMessage":
        role = SpeakerRole.SYSTEM.value
        msg_type = "system"
    elif isinstance(msg, ChatMessage) or cls_name == "ChatMessage":
        role = getattr(msg, "role", SpeakerRole.INTERVIEWER.value)
        msg_type = "chat"
    elif hasattr(msg, "additional_kwargs") and "role" in msg.additional_kwargs:
        role = str(msg.additional_kwargs["role"]).lower()
        msg_type = "human" if role == SpeakerRole.CANDIDATE.value else "ai"

    return {
        "type": msg_type,
        "role": role,
        "content": str(msg.content),
        "additional_kwargs": dict(getattr(msg, "additional_kwargs", {}) or {}),
        "id": getattr(msg, "id", None),
        "name": getattr(msg, "name", None),
    }



def deserialize_message(data: dict[str, Any]) -> BaseMessage:
    """Reconstruct a LangChain BaseMessage instance from a serialized message dict.

    Args:
        data: Serialized message dictionary.

    Returns:
        Instantiated HumanMessage, AIMessage, SystemMessage, or ChatMessage.
    """
    content = str(data.get("content", ""))
    additional_kwargs = dict(data.get("additional_kwargs", {}) or {})
    msg_id = data.get("id")
    name = data.get("name")
    role = str(data.get("role", "")).lower()
    msg_type = str(data.get("type", "")).lower()

    if msg_type == "human" or role == SpeakerRole.CANDIDATE.value or role == "user":
        return HumanMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            id=msg_id,
            name=name,
        )
    elif msg_type == "system" or role == SpeakerRole.SYSTEM.value:
        return SystemMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            id=msg_id,
            name=name,
        )
    elif role and role not in (SpeakerRole.INTERVIEWER.value, "assistant"):
        return ChatMessage(
            role=role,
            content=content,
            additional_kwargs=additional_kwargs,
            id=msg_id,
            name=name,
        )
    else:
        return AIMessage(
            content=content,
            additional_kwargs=additional_kwargs,
            id=msg_id,
            name=name,
        )


def serialize_state(state: InterviewState | dict[str, Any]) -> dict[str, Any]:
    """Convert an InterviewState into a purely JSON-serializable dictionary.

    Converts LangChain messages to serialized dictionaries, converts enums to string
    values, and handles dates/UUIDs.

    Args:
        state: The interview state to serialize.

    Returns:
        Fully JSON-serializable dictionary.
    """
    raw_dict = dict(state)
    result: dict[str, Any] = {}

    for key, value in raw_dict.items():
        if key == "messages":
            raw_messages = value or []
            result["messages"] = [serialize_message(m) for m in raw_messages]
        elif isinstance(value, Enum):
            result[key] = value.value
        elif isinstance(value, (UUID, datetime, date)):
            result[key] = str(value)
        elif isinstance(value, (list, tuple)):
            result[key] = [
                v.value if isinstance(v, Enum) else (str(v) if isinstance(v, (UUID, datetime)) else v)
                for v in value
            ]
        elif isinstance(value, dict):
            # Recursively handle inner dict values
            clean_dict: dict[str, Any] = {}
            for k, v in value.items():
                if isinstance(v, Enum):
                    clean_dict[k] = v.value
                elif isinstance(v, (UUID, datetime, date)):
                    clean_dict[k] = str(v)
                else:
                    clean_dict[k] = v
            result[key] = clean_dict
        else:
            result[key] = value

    return result


def deserialize_state(
    serialized: dict[str, Any],
    *,
    restore_messages: bool = True,
) -> InterviewState:
    """Reconstruct an `InterviewState` TypedDict from a serialized dictionary.

    Initializes baseline defaults if any required keys are omitted, and converts
    serialized message dicts back into LangChain `BaseMessage` objects.

    Args:
        serialized: Serialized state dictionary (e.g. from database or JSON checkpoint).
        restore_messages: Whether to convert message dicts into BaseMessage instances.

    Returns:
        Fully hydrated `InterviewState` TypedDict.
    """
    session_id = str(serialized.get("session_id", ""))
    user_id = str(serialized.get("user_id", ""))
    problem_slug = str(serialized.get("problem_slug", ""))
    problem_title = str(serialized.get("problem_title", ""))

    baseline = create_initial_state(
        session_id=session_id,
        user_id=user_id,
        problem_slug=problem_slug,
        problem_title=problem_title,
    )

    result_state = dict(baseline)
    result_state.update(serialized)

    if restore_messages and "messages" in serialized:
        restored_messages: list[BaseMessage | dict[str, Any]] = []
        for m in serialized.get("messages", []):
            if isinstance(m, dict):
                restored_messages.append(deserialize_message(m))
            elif isinstance(m, BaseMessage):
                restored_messages.append(m)
            else:
                restored_messages.append(m)
        result_state["messages"] = restored_messages

    return result_state  # type: ignore[return-value]


def state_to_json(
    state: InterviewState | dict[str, Any],
    *,
    indent: int | None = None,
) -> str:
    """Serialize an InterviewState directly to a JSON string.

    Args:
        state: Interview state.
        indent: Optional indentation level for pretty printing.

    Returns:
        JSON string representation.
    """
    serialized = serialize_state(state)
    return json.dumps(serialized, cls=StateJSONEncoder, indent=indent, ensure_ascii=False)


def state_from_json(json_str: str, *, restore_messages: bool = True) -> InterviewState:
    """Deserialize an InterviewState directly from a JSON string.

    Args:
        json_str: JSON formatted state string.
        restore_messages: Whether to restore message objects.

    Returns:
        Hydrated InterviewState TypedDict.
    """
    data = json.loads(json_str)
    if not isinstance(data, dict):
        raise ValueError("Decoded JSON root must be an object dictionary.")
    return deserialize_state(data, restore_messages=restore_messages)


def sanitize_state_for_audit(
    state: InterviewState | dict[str, Any],
    max_content_length: int = 500,
) -> dict[str, Any]:
    """Create a sanitized, lightweight state snapshot suitable for audit logging.

    Truncates very long message contents or whiteboard diagrams to avoid log bloat.

    Args:
        state: Interview state dictionary.
        max_content_length: Maximum string length for message content in logs.

    Returns:
        Sanitized state dictionary.
    """
    serialized = serialize_state(state)

    # Truncate messages if overly long
    sanitized_messages: list[dict[str, Any]] = []
    for msg in serialized.get("messages", []):
        if isinstance(msg, dict):
            c = str(msg.get("content", ""))
            truncated_content = c if len(c) <= max_content_length else f"{c[:max_content_length]}... [truncated]"
            sanitized_msg = dict(msg)
            sanitized_msg["content"] = truncated_content
            sanitized_messages.append(sanitized_msg)
        else:
            sanitized_messages.append(msg)
    serialized["messages"] = sanitized_messages

    # Truncate active artifact diagrams if very large
    artifacts = serialized.get("active_artifacts", {})
    if isinstance(artifacts, dict):
        clean_artifacts: dict[str, Any] = {}
        for k, v in artifacts.items():
            if isinstance(v, str) and len(v) > max_content_length:
                clean_artifacts[k] = f"{v[:max_content_length]}... [diagram truncated]"
            else:
                clean_artifacts[k] = v
        serialized["active_artifacts"] = clean_artifacts

    return serialized

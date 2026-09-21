"""System Design Interview Simulator - LangGraph Runnable Configuration.

Defines execution configurations, thread/checkpoint resolution, LangGraph
RunnableConfig converters, model hyperparameters, and execution metadata
orchestrating interview state machine invocations.
"""

from dataclasses import asdict, dataclass, field
from typing import Any, Final

from app.core.constants import InterviewerPersona, SeniorityLevel

DEFAULT_RECURSION_LIMIT: Final[int] = 50
DEFAULT_TEMPERATURE: Final[float] = 0.2
DEFAULT_MAX_TOKENS: Final[int] = 2048
THREAD_ID_PREFIX: Final[str] = "interview_session_"


def get_thread_id_for_session(session_id: str) -> str:
    """Derive deterministic LangGraph thread ID from interview session ID.

    Args:
        session_id: UUID or string session identifier.

    Returns:
        Formatted thread identifier string.
    """
    cleaned = str(session_id).strip()
    if cleaned.startswith(THREAD_ID_PREFIX):
        return cleaned
    return f"{THREAD_ID_PREFIX}{cleaned}"


def parse_session_id_from_thread_id(thread_id: str) -> str | None:
    """Extract session ID from deterministic LangGraph thread ID.

    Args:
        thread_id: Formatted thread identifier.

    Returns:
        Original session ID or None if not recognized.
    """
    cleaned = str(thread_id).strip()
    if cleaned.startswith(THREAD_ID_PREFIX):
        return cleaned[len(THREAD_ID_PREFIX):]
    return cleaned if cleaned else None


@dataclass
class GraphConfig:
    """Typed execution configuration for LangGraph state machine runs."""

    session_id: str
    user_id: str
    thread_id: str = ""
    checkpoint_id: str | None = None
    checkpoint_ns: str = ""
    persona: str = InterviewerPersona.COLLABORATIVE.value
    seniority_level: str = SeniorityLevel.SENIOR.value
    model_name: str = "gpt-4o"
    temperature: float = DEFAULT_TEMPERATURE
    max_tokens: int = DEFAULT_MAX_TOKENS
    recursion_limit: int = DEFAULT_RECURSION_LIMIT
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure thread_id and tags are properly initialized."""
        if not self.thread_id:
            self.thread_id = get_thread_id_for_session(self.session_id)
        if "interview-simulator" not in self.tags:
            self.tags.append("interview-simulator")
        if self.persona and self.persona not in self.tags:
            self.tags.append(self.persona)

    def to_runnable_config(self) -> dict[str, Any]:
        """Convert into standard LangGraph/LangChain `RunnableConfig` dictionary format."""
        configurable: dict[str, Any] = {
            "thread_id": self.thread_id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "persona": self.persona,
            "seniority_level": self.seniority_level,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "checkpoint_ns": self.checkpoint_ns,
        }
        if self.checkpoint_id is not None:
            configurable["checkpoint_id"] = self.checkpoint_id

        meta = dict(self.metadata)
        meta.setdefault("session_id", self.session_id)
        meta.setdefault("user_id", self.user_id)

        return {
            "configurable": configurable,
            "recursion_limit": self.recursion_limit,
            "tags": list(self.tags),
            "metadata": meta,
        }

    @classmethod
    def from_runnable_config(cls, config: dict[str, Any] | None) -> "GraphConfig":
        """Extract typed GraphConfig from a LangGraph `RunnableConfig` dictionary."""
        if not config:
            return cls(session_id="unknown", user_id="unknown")

        configurable = config.get("configurable", {})
        session_id = str(
            configurable.get("session_id")
            or parse_session_id_from_thread_id(configurable.get("thread_id", ""))
            or "unknown"
        )
        user_id = str(configurable.get("user_id") or "unknown")
        thread_id = str(configurable.get("thread_id") or get_thread_id_for_session(session_id))
        checkpoint_id = configurable.get("checkpoint_id")
        checkpoint_ns = str(configurable.get("checkpoint_ns", ""))

        persona = str(configurable.get("persona") or InterviewerPersona.COLLABORATIVE.value)
        seniority = str(configurable.get("seniority_level") or SeniorityLevel.SENIOR.value)
        model_name = str(configurable.get("model_name") or "gpt-4o")
        temperature = float(configurable.get("temperature", DEFAULT_TEMPERATURE))
        max_tokens = int(configurable.get("max_tokens", DEFAULT_MAX_TOKENS))

        recursion_limit = int(config.get("recursion_limit", DEFAULT_RECURSION_LIMIT))
        tags = list(config.get("tags", []))
        metadata = dict(config.get("metadata", {}))

        return cls(
            session_id=session_id,
            user_id=user_id,
            thread_id=thread_id,
            checkpoint_id=checkpoint_id,
            checkpoint_ns=checkpoint_ns,
            persona=persona,
            seniority_level=seniority,
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            recursion_limit=recursion_limit,
            tags=tags,
            metadata=metadata,
        )


def create_graph_config(
    session_id: str,
    user_id: str,
    *,
    persona: str = InterviewerPersona.COLLABORATIVE.value,
    seniority_level: str = SeniorityLevel.SENIOR.value,
    model_name: str = "gpt-4o",
    checkpoint_id: str | None = None,
    recursion_limit: int = DEFAULT_RECURSION_LIMIT,
    extra_tags: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> GraphConfig:
    """Factory helper creating an initialized GraphConfig instance.

    Args:
        session_id: Interview session identifier.
        user_id: Candidate user identifier.
        persona: Interviewer persona style.
        seniority_level: Candidate seniority calibration.
        model_name: Target LLM model name.
        checkpoint_id: Optional checkpoint ID to resume from.
        recursion_limit: Maximum graph recursion depth.
        extra_tags: Optional additional telemetry tags.
        metadata: Optional dictionary of operational metadata.

    Returns:
        Configured GraphConfig instance.
    """
    tags = ["interview-simulator", persona]
    if extra_tags:
        tags.extend(extra_tags)

    return GraphConfig(
        session_id=session_id,
        user_id=user_id,
        persona=persona,
        seniority_level=seniority_level,
        model_name=model_name,
        checkpoint_id=checkpoint_id,
        recursion_limit=recursion_limit,
        tags=tags,
        metadata=metadata or {},
    )

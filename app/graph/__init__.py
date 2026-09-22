"""System Design Interview Simulator - LangGraph Orchestration Package.

Exports state machine definitions, state containers, stage transition logic,
execution checkpointers, event streaming wrappers, and graph builder utilities
governing the multi-turn AI system design interview workflow.
"""

from typing import Any

# Dynamic mapping of exported symbols to their submodule source
_EXPORTS: dict[str, str] = {
    # State & Channels (Task 092, Task 099)
    "InterviewState": "app.graph.state",
    "create_initial_state": "app.graph.state",
    "append_messages_reducer": "app.graph.state",
    "merge_dict_reducer": "app.graph.state",
    # Stages & Prerequisites (Task 093)
    "InterviewStage": "app.graph.stages",
    "STAGE_PREREQUISITES": "app.graph.stages",
    "STAGE_TIME_ALLOCATIONS": "app.graph.stages",
    "get_next_stage": "app.graph.stages",
    "get_previous_stage": "app.graph.stages",
    "is_stage_accessible": "app.graph.stages",
    # Context (Task 094)
    "InterviewContext": "app.graph.context",
    # Checkpointers (Task 095)
    "BaseCheckpointerProvider": "app.graph.checkpointer",
    "InMemoryCheckpointerProvider": "app.graph.checkpointer",
    "PostgresCheckpointerProvider": "app.graph.checkpointer",
    "get_checkpointer": "app.graph.checkpointer",
    # Events & Streaming (Task 096)
    "GraphEvent": "app.graph.events",
    "GraphEventType": "app.graph.events",
    "TokenStreamEvent": "app.graph.events",
    "StageTransitionEvent": "app.graph.events",
    # Modifiers & Guards (Task 097, Task 098)
    "append_turn": "app.graph.modifiers",
    "evaluate_stage_exit_guards": "app.graph.guards",
    # Config & Types (Task 100, Task 101)
    "GraphConfig": "app.graph.config",
    "CandidateAction": "app.graph.types",
    # State History & Traversal (Task 103)
    "StateHistoryReconstructor": "app.graph.state_history",
    "SessionTimeline": "app.graph.state_history",
    "StageHistoryRecord": "app.graph.state_history",
    "build_linear_execution_path": "app.graph.state_history",
    "reconstruct_stage_history": "app.graph.state_history",
    # Metrics & Telemetry (Task 104)
    "GraphMetricsCollector": "app.graph.metrics",
    "NodeExecutionMetric": "app.graph.metrics",
    "StageMetricsSummary": "app.graph.metrics",
    "SessionMetricsSummary": "app.graph.metrics",
    "measure_node_execution": "app.graph.metrics",
    # Builder (Task 139)
    "build_interview_graph": "app.graph.builder",
    "compile_interview_graph": "app.graph.builder",
}


def __getattr__(name: str) -> Any:
    """Dynamically import graph components on demand to support incremental builds."""
    if name in _EXPORTS:
        module_path = _EXPORTS[name]
        try:
            module = __import__(module_path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError) as err:
            raise AttributeError(
                f"Graph component '{name}' is not yet available in module '{module_path}': {err}"
            ) from err
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # State & Reducers
    "InterviewState",
    "create_initial_state",
    "append_messages_reducer",
    "merge_dict_reducer",
    # Stages & Progression
    "InterviewStage",
    "STAGE_PREREQUISITES",
    "STAGE_TIME_ALLOCATIONS",
    "get_next_stage",
    "get_previous_stage",
    "is_stage_accessible",
    # Context
    "InterviewContext",
    # Persistence & Checkpointing
    "BaseCheckpointerProvider",
    "InMemoryCheckpointerProvider",
    "PostgresCheckpointerProvider",
    "get_checkpointer",
    # Events & Telemetry
    "GraphEvent",
    "GraphEventType",
    "TokenStreamEvent",
    "StageTransitionEvent",
    # Modifiers & Guards
    "append_turn",
    "evaluate_stage_exit_guards",
    # Config & Types
    "GraphConfig",
    "CandidateAction",
    # State History & Traversal
    "StateHistoryReconstructor",
    "SessionTimeline",
    "StageHistoryRecord",
    "build_linear_execution_path",
    "reconstruct_stage_history",
    # Metrics & Telemetry
    "GraphMetricsCollector",
    "NodeExecutionMetric",
    "StageMetricsSummary",
    "SessionMetricsSummary",
    "measure_node_execution",
    # Graph Construction
    "build_interview_graph",
    "compile_interview_graph",
]

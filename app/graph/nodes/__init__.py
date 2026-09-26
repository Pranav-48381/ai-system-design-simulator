"""System Design Interview Simulator - LangGraph Node Handlers Package.

Exports state graph node implementations governing dialogue routing, stage-specific
probing (clarification, capacity estimation, high-level architecture, deep dive, bottlenecks),
conversational response synthesis, hints, evaluations, canvas synchronization,
timeout handling, and error fallbacks.
"""

from typing import Any

# Dynamic mapping of exported node functions to their submodule sources
_EXPORTS: dict[str, str] = {
    # Routing & Flow Control (Task 122)
    "router_node": "app.graph.nodes.router_node",
    # Stage-Specific Probing Nodes (Tasks 123 - 127)
    "clarification_node": "app.graph.nodes.clarification_node",
    "estimation_node": "app.graph.nodes.estimation_node",
    "architecture_node": "app.graph.nodes.architecture_node",
    "deep_dive_node": "app.graph.nodes.deep_dive_node",
    "bottleneck_node": "app.graph.nodes.bottleneck_node",
    # Interviewer Response & Hint Generation (Tasks 128 - 129)
    "interviewer_node": "app.graph.nodes.interviewer_node",
    "hint_node": "app.graph.nodes.hint_node",
    # Evaluation & Debrief Nodes (Tasks 130 - 132)
    "stage_evaluator_node": "app.graph.nodes.stage_evaluator_node",
    "final_evaluator_node": "app.graph.nodes.final_evaluator_node",
    "report_node": "app.graph.nodes.report_node",
    # Canvas, Timeout & Resilient Fallback Nodes (Tasks 133 - 135)
    "canvas_node": "app.graph.nodes.canvas_node",
    "timeout_node": "app.graph.nodes.timeout_node",
    "error_fallback_node": "app.graph.nodes.error_fallback_node",
}


def __getattr__(name: str) -> Any:
    """Dynamically import graph node handlers on demand to support incremental loading."""
    if name in _EXPORTS:
        module_path = _EXPORTS[name]
        try:
            module = __import__(module_path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError) as err:
            raise AttributeError(
                f"Graph node handler '{name}' is not yet available in module '{module_path}': {err}"
            ) from err
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Routing & Intent
    "router_node",
    # Stage Probing Nodes
    "clarification_node",
    "estimation_node",
    "architecture_node",
    "deep_dive_node",
    "bottleneck_node",
    # Interviewer & Guidance
    "interviewer_node",
    "hint_node",
    # Evaluation & Reporting
    "stage_evaluator_node",
    "final_evaluator_node",
    "report_node",
    # Canvas & System Nodes
    "canvas_node",
    "timeout_node",
    "error_fallback_node",
]

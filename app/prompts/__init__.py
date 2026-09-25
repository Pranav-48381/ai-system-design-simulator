"""System Design Interview Simulator - Prompt Engineering Package.

Exports system prompt templates, persona instructions, stage-specific guidance,
formatting utilities, few-shot blueprints, and prompt builders orchestrating
interviewer behavior across the multi-stage system design evaluation lifecycle.
"""

from typing import Any

# Dynamic mapping of exported prompt utilities and templates to their submodule sources
_EXPORTS: dict[str, str] = {
    # Base Prompts & Formatting Helpers (Task 107)
    "BasePromptBuilder": "app.prompts.base",
    "PromptContext": "app.prompts.base",
    "render_base_system_prompt": "app.prompts.base",
    "format_dialogue_history": "app.prompts.base",
    "format_artifact_context": "app.prompts.base",
    "format_seniority_expectations": "app.prompts.base",
    # Persona Prompts (Task 108)
    "get_persona_prompt": "app.prompts.personas",
    "PERSONA_PROMPTS": "app.prompts.personas",
    "COLLABORATIVE_STAFF_PERSONA": "app.prompts.personas",
    "RIGOROUS_PRINCIPAL_PERSONA": "app.prompts.personas",
    "SOCRATIC_ARCHITECT_PERSONA": "app.prompts.personas",
    "CHALLENGING_SPECIALIST_PERSONA": "app.prompts.personas",
    # Stage-Specific Prompts (Tasks 109 - 114)
    "get_clarification_prompt": "app.prompts.clarification",
    "get_estimation_prompt": "app.prompts.estimation",
    "get_architecture_prompt": "app.prompts.architecture",
    "get_deep_dive_prompt": "app.prompts.deep_dive",
    "get_bottleneck_prompt": "app.prompts.bottleneck",
    "get_router_intent_prompt": "app.prompts.router",
    "get_stage_readiness_prompt": "app.prompts.router",
    "get_evaluation_prompt": "app.prompts.evaluation",
    # Hints & Rubrics (Tasks 115 - 117)
    "get_rubric_evaluation_prompt": "app.prompts.rubric_eval",
    "get_single_pillar_evaluation_prompt": "app.prompts.rubric_eval",
    "get_final_summary_prompt": "app.prompts.final_summary",
    "get_executive_summary_prompt": "app.prompts.final_summary",
    "get_improvement_tips_prompt": "app.prompts.final_summary",
    "get_hint_prompt": "app.prompts.hint_generator",
    "get_progressive_hint_prompt": "app.prompts.hint_generator",
}


def __getattr__(name: str) -> Any:
    """Dynamically import prompt utilities on demand to support incremental builds."""
    if name in _EXPORTS:
        module_path = _EXPORTS[name]
        try:
            module = __import__(module_path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError) as err:
            raise AttributeError(
                f"Prompt component '{name}' is not yet available in module '{module_path}': {err}"
            ) from err
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")


__all__ = [
    # Base Foundation & Builders
    "BasePromptBuilder",
    "PromptContext",
    "render_base_system_prompt",
    "format_dialogue_history",
    "format_artifact_context",
    "format_seniority_expectations",
    # Personas
    "get_persona_prompt",
    "PERSONA_PROMPTS",
    "COLLABORATIVE_STAFF_PERSONA",
    "RIGOROUS_PRINCIPAL_PERSONA",
    "SOCRATIC_ARCHITECT_PERSONA",
    "CHALLENGING_SPECIALIST_PERSONA",
    # Stage & Router Prompts
    "get_clarification_prompt",
    "get_estimation_prompt",
    "get_architecture_prompt",
    "get_deep_dive_prompt",
    "get_bottleneck_prompt",
    "get_router_intent_prompt",
    "get_stage_readiness_prompt",
    "get_evaluation_prompt",
    # Hints, Rubrics & Summaries
    "get_hint_prompt",
    "get_progressive_hint_prompt",
    "get_rubric_evaluation_prompt",
    "get_single_pillar_evaluation_prompt",
    "get_final_summary_prompt",
    "get_executive_summary_prompt",
    "get_improvement_tips_prompt",
]

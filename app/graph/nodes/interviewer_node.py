"""System Design Interview Simulator - Interviewer Node Implementation.

Executes conversational response synthesis and general dialogue facilitation.
Blends the selected interviewer persona (Collaborative Staff, Rigorous Principal, Socratic Architect,
or Challenging Specialist) with current stage objectives and seniority-calibrated feedback.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, InterviewerPersona, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.state import InterviewState
from app.graph.types import InterviewerNodeOutput
from app.prompts.base import BasePromptBuilder, PromptContext
from app.prompts.personas import get_persona_config, get_persona_prompt

logger = logging.getLogger(__name__)


def generate_fallback_interviewer_response(
    ctx: InterviewContext,
    candidate_text: str,
) -> str:
    """Generate persona-aligned deterministic conversational response when LLM is unavailable."""
    persona = ctx.persona.lower()
    stage = ctx.current_stage.value
    seniority = ctx.seniority_level.lower()
    topic = ctx.problem_title or "the architecture"

    if "socratic" in persona:
        return (
            f"That is an interesting direction for {topic}. "
            "Let's reflect on the trade-offs: if we optimize heavily for this dimension, "
            "what compromises are we introducing for availability and system complexity in the current stage?"
        )

    if "rigorous" in persona or "principal" in persona:
        reply = (
            f"Understood. Moving forward in the {stage} phase, let's ensure our architectural assumptions are precise. "
            "At scale, what are the exact failure domains, resource constraints, and data consistency models "
            "you are committing to?"
        )
        if seniority == SeniorityLevel.STAFF.value:
            reply += " I expect clear justification backed by operational SLOs and blast radius limits."
        return reply

    if "challenging" in persona:
        return (
            f"Let's stress-test that assertion for {topic}. "
            "What happens if our downstream dependencies experience an order-of-magnitude increase in latency? "
            "How does your proposal prevent cascading failures under peak load?"
        )

    # Default to Collaborative Staff
    return (
        f"Thanks for walking me through your thinking on {topic}. "
        f"In this {stage} stage, let's keep building on that foundation. "
        "What key aspect or component would you like to drill into next?"
    )


async def interviewer_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> InterviewerNodeOutput:
    """Synthesize persona-driven interviewer dialogue response.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        InterviewerNodeOutput dictionary with updated dialogue turns and counters.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()

    # 1. Prepare prompt context
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=ctx.current_stage.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
        artifacts=state.get("active_artifacts", {}),
        calculations=ctx.get_calculations(),
        satisfied_criteria=ctx.get_satisfied_criteria(),
        candidate_name=ctx.candidate_name,
    )

    cfg = config or {}
    configurable = cfg.get("configurable", {})
    llm_client = configurable.get("llm_client")

    interviewer_reply: str | None = None

    # 2. Invoke LLM if available
    if llm_client is not None:
        try:
            persona_instructions = get_persona_prompt(ctx.persona, stage=ctx.current_stage)
            builder = BasePromptBuilder(prompt_ctx).with_persona(persona_instructions)
            builder.with_stage_instruction(
                f"You are the technical interviewer facilitating the {ctx.current_stage.value} stage. "
                "Respond conversationally to the candidate's latest remark, answer any direct questions, "
                "and guide the discussion productively forward while maintaining your assigned persona tone."
            )
            prompt = builder.build_system_prompt()

            response = None
            if hasattr(llm_client, "ainvoke"):
                response = await llm_client.ainvoke(prompt)
            elif hasattr(llm_client, "invoke"):
                response = llm_client.invoke(prompt)

            if response is not None:
                interviewer_reply = getattr(response, "content", str(response)).strip()
        except Exception as err:
            logger.warning("LLM invocation failed in interviewer_node, falling back: %s", err)

    # 3. Calibrated deterministic fallback
    if not interviewer_reply:
        interviewer_reply = generate_fallback_interviewer_response(
            ctx=ctx,
            candidate_text=latest_candidate_text,
        )

    # 4. Build turn update
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=interviewer_reply,
        metadata={
            "stage": ctx.current_stage.value,
            "node": "interviewer_node",
            "persona": ctx.persona,
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "next_node": None,
    }

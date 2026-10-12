"""System Design Interview Simulator - Hint Node Implementation.

Executes the progressive 3-tier hint generator node.
Provides calibrated, unblocking guidance (Tier 1: Conceptual Nudge,
Tier 2: Scoped Boundary, Tier 3: Architectural Options) without premature solution disclosure.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.state import InterviewState
from app.graph.types import HintNodeOutput
from app.prompts.base import PromptContext
from app.prompts.hint_generator import get_progressive_hint_prompt
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Fallback deterministic hints organized by stage and tier
FALLBACK_STAGE_HINTS: dict[str, dict[int, str]] = {
    InterviewStage.CLARIFICATION.value: {
        1: "Consider what scope constraints or non-functional SLAs (such as availability vs latency budgets) define system success.",
        2: "Notice whether this system's access pattern is primarily read-heavy or write-heavy, and what consistency guarantees (strict vs eventual) are acceptable.",
        3: "You can prioritize either strict ACID consistency with relational storage or high availability with eventual consistency (BASE). Which aligns better with user expectations?",
    },
    InterviewStage.ESTIMATION.value: {
        1: "Start from Daily Active Users (DAU) and estimate the average operations per user to deduce average and peak QPS.",
        2: "A single relational database typically bottlenecks at 10,000 write QPS. If your peak traffic exceeds that, consider horizontal distribution and memory footprint.",
        3: "Convert QPS into storage by assuming an average payload size (e.g. 500 bytes per record) and projecting the capacity needed over a 5-year retention horizon.",
    },
    InterviewStage.ARCHITECTURE.value: {
        1: "Trace the request lifecycle step-by-step from client ingress at DNS/CDN through the load balancer to your backend services.",
        2: "A single application server cannot sustain peak ingress; separate your stateless API services from stateful storage, and use load balancing.",
        3: "Compare synchronous REST/gRPC endpoints behind an API Gateway with an asynchronous event-driven message queue for heavy write processing.",
    },
    InterviewStage.DEEP_DIVE.value: {
        1: "Examine your primary data access patterns: what query filters and join requirements dictate your schema and secondary indexes?",
        2: "When database volume exceeds a single node's IOPS or storage limits, how do you select a horizontal sharding key to distribute data evenly?",
        3: "Evaluate range-based partitioning versus consistent hashing with virtual nodes. How does each choice handle re-sharding and celebrity hotspots?",
    },
    InterviewStage.BOTTLENECK.value: {
        1: "Inspect the architecture canvas for Single Points of Failure (SPOFs) across availability zones, databases, and third-party dependencies.",
        2: "When a downstream service degrades or becomes unreachable, upstream services risk thread exhaustion. Where can you place circuit breakers and bulkheads?",
        3: "Compare Token Bucket versus Sliding Window Counter rate limiting at the API Gateway to shed sudden traffic spikes and protect core backends.",
    },
}


def generate_fallback_hint(stage: str, tier: int) -> str:
    """Retrieve calibrated deterministic hint based on active stage and tier level."""
    stage_hints = FALLBACK_STAGE_HINTS.get(stage, FALLBACK_STAGE_HINTS[InterviewStage.CLARIFICATION.value])
    clamped_tier = max(1, min(3, tier))
    return stage_hints.get(clamped_tier, stage_hints[1])


async def hint_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> HintNodeOutput:
    """Generate progressive, unblocking guidance calibrated to candidate seniority.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        HintNodeOutput dictionary with updated dialogue, hint history, and turn counters.
    """
    ctx = InterviewContext(state)
    current_stage = ctx.current_stage.value
    prior_hints: list[dict[str, Any]] = list(state.get("hints_used", []))
    hint_tier = min(3, len(prior_hints) + 1)

    # 1. Prepare prompt context
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=current_stage,
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

    hint_text: str | None = None
    pedagogical_intent: str = ""

    # 2. Invoke LLM if available
    if llm_client is not None:
        try:
            persona_instructions = get_persona_prompt(ctx.persona, stage=ctx.current_stage)
            prompt = get_progressive_hint_prompt(
                context=prompt_ctx,
                previous_hints=prior_hints,
                topic=current_stage,
                persona_prompt=persona_instructions,
            )

            response = None
            if hasattr(llm_client, "ainvoke"):
                response = await llm_client.ainvoke(prompt)
            elif hasattr(llm_client, "invoke"):
                response = llm_client.invoke(prompt)

            if response is not None:
                content = getattr(response, "content", str(response)).strip()
                # Parse JSON payload
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    hint_text = parsed.get("hint_text", "").strip()
                    pedagogical_intent = parsed.get("pedagogical_intent", "")
                elif content:
                    hint_text = content
        except Exception as err:
            logger.warning("LLM invocation failed in hint_node, falling back: %s", err)

    # 3. Deterministic fallback if LLM omitted or failed
    if not hint_text:
        hint_text = generate_fallback_hint(current_stage, hint_tier)
        pedagogical_intent = f"Deterministic Tier {hint_tier} progressive hint for {current_stage}."

    # 4. Record hint in history
    hint_record: dict[str, Any] = {
        "tier": hint_tier,
        "hint_text": hint_text,
        "pedagogical_intent": pedagogical_intent,
        "stage": current_stage,
        "timestamp": time.time(),
    }

    # Format interviewer reply
    interviewer_reply = f"[Hint - Tier {hint_tier}]: {hint_text}"

    # 5. Append turn
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=interviewer_reply,
        metadata={
            "stage": current_stage,
            "node": "hint_node",
            "is_hint": True,
            "hint_tier": hint_tier,
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "hint_count": len(prior_hints) + 1,
        "hints_used": [hint_record],
        "next_node": None,
    }

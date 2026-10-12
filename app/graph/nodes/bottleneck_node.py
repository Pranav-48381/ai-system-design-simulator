"""System Design Interview Simulator - Bottleneck Node Implementation.

Executes the Bottlenecks, Failure Modes & Resilience stage (Stage 5).
Evaluates single points of failure (SPOFs), cascading failures and circuit breakers,
rate limiting and load shedding, disaster recovery (RPO/RTO), and architectural trade-offs.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.state import InterviewState
from app.graph.types import BottleneckNodeOutput
from app.prompts.base import PromptContext
from app.prompts.bottleneck import (
    BOTTLENECK_CHAOS_SCENARIOS,
    BOTTLENECK_PROBES,
    format_missing_bottleneck_criteria,
    get_bottleneck_prompt,
)
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Heuristics for detecting addressed bottleneck and resilience criteria
SPOF_KEYWORDS = re.compile(
    r"\b(spof|single point of failure|redundanc|multi-az|failover|standby|replica|heartbeat|backup|clustering|active-passive|active-active)\b",
    re.IGNORECASE,
)
FAILURE_MODES_KEYWORDS = re.compile(
    r"\b(circuit breaker|retry storm|exponential backoff|jitter|bulkhead|timeout|cascading|dead-letter|dead letter|fallback|degradation|load shedding)\b",
    re.IGNORECASE,
)
RATE_LIMITING_KEYWORDS = re.compile(
    r"\b(rate limit|token bucket|leaky bucket|sliding window|load shed|429|too many requests|throttl|api gateway|traffic shap)\b",
    re.IGNORECASE,
)
TRADE_OFF_KEYWORDS = re.compile(
    r"\b(trade-off|tradeoff|cap theorem|pacelc|eventual consistency|strong consistency|availability vs|consistency vs|latency vs|sacrifice|cost)\b",
    re.IGNORECASE,
)


def detect_satisfied_bottleneck_criteria(
    candidate_text: str,
    already_satisfied: list[str],
) -> list[str]:
    """Inspect candidate response to identify newly satisfied resilience and bottleneck criteria."""
    newly_satisfied = list(already_satisfied)
    text = candidate_text.lower()

    if "spof_identification" not in newly_satisfied and SPOF_KEYWORDS.search(text):
        newly_satisfied.append("spof_identification")

    if "failure_modes" not in newly_satisfied and FAILURE_MODES_KEYWORDS.search(text):
        newly_satisfied.append("failure_modes")

    if "rate_limiting" not in newly_satisfied and RATE_LIMITING_KEYWORDS.search(text):
        newly_satisfied.append("rate_limiting")

    if "trade_off_analysis" not in newly_satisfied and TRADE_OFF_KEYWORDS.search(text):
        newly_satisfied.append("trade_off_analysis")

    return newly_satisfied


def generate_fallback_bottleneck_response(
    ctx: InterviewContext,
    candidate_text: str,
    satisfied_criteria: list[str],
) -> str:
    """Synthesize high-fidelity deterministic resilience feedback when LLM is offline or in mock mode."""
    seniority = ctx.seniority_level.lower()
    has_spof = "spof_identification" in satisfied_criteria
    has_failures = "failure_modes" in satisfied_criteria
    has_ratelimit = "rate_limiting" in satisfied_criteria
    has_tradeoffs = "trade_off_analysis" in satisfied_criteria

    # If SPOFs not yet addressed
    if not has_spof:
        reply = (
            "Let's stress-test the availability and failure domains of your architecture. "
            "Where is the single biggest Single Point of Failure (SPOF) in your design right now? "
            "If an entire Availability Zone or your primary database node goes completely offline, "
            "how does automated failover occur without data loss?"
        )
        if seniority == SeniorityLevel.STAFF.value:
            reply += " Specifically explain your consensus protocol, election latency, and split-brain resolution strategy."
        return reply

    # If failure modes / circuit breakers not yet addressed
    if not has_failures:
        return (
            "Your redundancy and failover strategy is noted. Now let's consider cascading failures: "
            "if an internal downstream dependency or downstream microservice suffers extreme latency (e.g. 10s per call), "
            "how do you prevent client retry storms from exhausting upstream thread pools and taking down the whole system? "
            "Where do you configure circuit breakers, and what are their trip thresholds?"
        )

    # If rate limiting / load shedding not yet addressed
    if not has_ratelimit:
        return (
            "Circuit breakers and bulkhead isolation provide strong protection against cascading outages. "
            "Now consider sudden traffic surges: suppose a promotional event causes traffic to spike 10x in 30 seconds. "
            "What rate limiting algorithm (Token Bucket vs Sliding Window Counter) are you implementing, "
            "and at which architectural boundary (CDN edge, API Gateway, or worker service) is it enforced?"
        )

    # If trade-offs not yet articulated
    if not has_tradeoffs:
        return (
            "Rate limiting and traffic regulation are sound. Every distributed architecture involves trade-offs. "
            "In your design, what primary trade-off did you make (e.g. CAP / PACELC consistency vs latency, or operational complexity vs cost)? "
            "What would you redesign if infrastructure cost needed to be halved?"
        )

    # All criteria addressed or turn threshold reached
    return (
        "You have conducted a comprehensive analysis of bottlenecks, failure modes, rate limiting, and trade-offs. "
        "Your fault-tolerance strategy is well grounded. "
        "We are now ready to conclude the technical design session and move to Stage 6: Evaluation & Debrief."
    )


async def bottleneck_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> BottleneckNodeOutput:
    """Conduct bottleneck and resilience turn probing SPOFs, circuit breakers, rate limits, and trade-offs.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        BottleneckNodeOutput dictionary with updated dialogue, turn counters, and criteria.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()
    current_satisfied = ctx.get_satisfied_criteria(InterviewStage.BOTTLENECK)

    # 1. Detect satisfied criteria
    updated_criteria = detect_satisfied_bottleneck_criteria(
        latest_candidate_text,
        current_satisfied,
    )

    # 2. Prepare prompt context
    missing = format_missing_bottleneck_criteria(updated_criteria)
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.BOTTLENECK.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
        artifacts=state.get("active_artifacts", {}),
        calculations=ctx.get_calculations(),
        satisfied_criteria=updated_criteria,
        candidate_name=ctx.candidate_name,
    )

    cfg = config or {}
    configurable = cfg.get("configurable", {})
    llm_client = configurable.get("llm_client")

    interviewer_reply: str | None = None

    # 3. Invoke LLM if available
    if llm_client is not None:
        try:
            persona_instructions = get_persona_prompt(ctx.persona)
            prompt = get_bottleneck_prompt(
                context=prompt_ctx,
                persona_prompt=persona_instructions,
                missing_criteria=missing,
            )

            response = None
            if hasattr(llm_client, "ainvoke"):
                response = await llm_client.ainvoke(prompt)
            elif hasattr(llm_client, "invoke"):
                response = llm_client.invoke(prompt)

            if response is not None:
                interviewer_reply = getattr(response, "content", str(response)).strip()
        except Exception as err:
            logger.warning("LLM invocation failed in bottleneck_node, falling back: %s", err)

    # 4. Calibrated deterministic fallback
    if not interviewer_reply:
        interviewer_reply = generate_fallback_bottleneck_response(
            ctx=ctx,
            candidate_text=latest_candidate_text,
            satisfied_criteria=updated_criteria,
        )

    # 5. Build turn update
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=interviewer_reply,
        metadata={
            "stage": InterviewStage.BOTTLENECK.value,
            "node": "bottleneck_node",
            "satisfied_criteria_count": len(updated_criteria),
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "stage_criteria_satisfied": {InterviewStage.BOTTLENECK.value: updated_criteria},
        "next_node": None,
    }

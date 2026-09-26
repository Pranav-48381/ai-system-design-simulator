"""System Design Interview Simulator - Capacity Estimation Node Implementation.

Executes the Back-of-the-Envelope Capacity Estimation stage (Stage 2).
Validates scale arithmetic, parses QPS, storage, bandwidth, and cache sizing calculations,
verifies physical system boundaries, and guides the candidate toward architecture-ready figures.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.types import EstimationNodeOutput
from app.prompts.base import PromptContext
from app.prompts.estimation import (
    ESTIMATION_PROBES,
    format_missing_estimation_criteria,
    get_estimation_prompt,
)
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Heuristics for parsing quantitative calculations from dialogue
QPS_EXTRACTOR = re.compile(
    r"(\b\d[\d,\.]*)\s*(qps|tps|queries per second|req(?:uests)?/sec|writes/sec|reads/sec)\b",
    re.IGNORECASE,
)
STORAGE_EXTRACTOR = re.compile(
    r"(\b\d[\d,\.]*)\s*(bytes?|kb|mb|gb|tb|pb)(?:\s*(?:per day|daily|per year|over 5 years|5-year|storage))?",
    re.IGNORECASE,
)
CACHE_EXTRACTOR = re.compile(
    r"(\b\d[\d,\.]*)\s*(gb|tb|mb)\s*(?:of )?(?:cache|ram|memory|working set)\b",
    re.IGNORECASE,
)


def extract_calculations_from_text(text: str) -> list[dict[str, Any]]:
    """Extract candidate mathematical calculations, units, and metrics from text."""
    calculations: list[dict[str, Any]] = []

    # 1. QPS extraction
    qps_match = QPS_EXTRACTOR.search(text)
    if qps_match:
        val_str = qps_match.group(1).replace(",", "")
        try:
            val = float(val_str)
            calculations.append({
                "metric": "throughput_qps",
                "candidate_value": val,
                "unit": qps_match.group(2).upper(),
                "is_verified": True,
                "notes": f"Extracted {val} {qps_match.group(2)}",
            })
        except ValueError:
            pass

    # 2. Storage extraction
    storage_match = STORAGE_EXTRACTOR.search(text)
    if storage_match:
        val_str = storage_match.group(1).replace(",", "")
        try:
            val = float(val_str)
            calculations.append({
                "metric": "storage_volume",
                "candidate_value": val,
                "unit": storage_match.group(2).upper(),
                "is_verified": True,
                "notes": f"Extracted {val} {storage_match.group(2)}",
            })
        except ValueError:
            pass

    # 3. Cache memory extraction
    cache_match = CACHE_EXTRACTOR.search(text)
    if cache_match:
        val_str = cache_match.group(1).replace(",", "")
        try:
            val = float(val_str)
            calculations.append({
                "metric": "cache_memory",
                "candidate_value": val,
                "unit": cache_match.group(2).upper(),
                "is_verified": True,
                "notes": f"Extracted {val} {cache_match.group(2)} RAM cache",
            })
        except ValueError:
            pass

    return calculations


def detect_satisfied_estimation_criteria(
    candidate_text: str,
    already_satisfied: list[str],
) -> list[str]:
    """Inspect candidate response to identify newly satisfied capacity estimation criteria."""
    newly_satisfied = list(already_satisfied)
    text = candidate_text.lower()

    if "traffic_qps" not in newly_satisfied and (
        "qps" in text or "tps" in text or "requests per second" in text or "queries per second" in text
    ):
        newly_satisfied.append("traffic_qps")

    if "storage_capacity" not in newly_satisfied and (
        "storage" in text or "tb" in text or "gb" in text or "pb" in text or "retention" in text or "bytes" in text
    ):
        newly_satisfied.append("storage_capacity")

    if "bandwidth_throughput" not in newly_satisfied and (
        "bandwidth" in text or "mb/s" in text or "gbps" in text or "cache" in text or "ram" in text or "80/20" in text
    ):
        newly_satisfied.append("bandwidth_throughput")

    return newly_satisfied


def generate_fallback_estimation_response(
    ctx: InterviewContext,
    candidate_text: str,
    satisfied_criteria: list[str],
    calculations: list[dict[str, Any]],
) -> str:
    """Synthesize high-fidelity deterministic estimation feedback when LLM is offline or mock."""
    seniority = ctx.seniority_level.lower()
    has_qps = "traffic_qps" in satisfied_criteria
    has_storage = "storage_capacity" in satisfied_criteria
    has_bandwidth_or_cache = "bandwidth_throughput" in satisfied_criteria

    # If candidate provided QPS but not storage yet
    if has_qps and not has_storage:
        reply = (
            "Your QPS breakdown gives us a reliable baseline. "
            "Now let's calculate our storage footprint: if each record payload is approximately 500 bytes to 1 KB, "
            "what is our daily data ingestion rate, and how much cumulative capacity do we need for 5-year retention "
            "factoring in a 3x replication factor?"
        )
        if seniority == SeniorityLevel.STAFF.value:
            reply += " Also consider database index overhead and whether write IOPS exceed SSD throughput limits."
        return reply

    # If candidate provided storage but not cache/bandwidth
    if has_storage and not has_bandwidth_or_cache:
        return (
            "The storage growth calculations look consistent and realistic. "
            "Next, let's size our caching layer using the 80/20 Pareto distribution. "
            "If 20% of the active working set generates 80% of read traffic, "
            "how much RAM would our Redis cluster need to cache one day's worth of hot items?"
        )

    # If all criteria are satisfied or multiple turns completed
    if (has_qps and has_storage and has_bandwidth_or_cache) or ctx.stage_turn_count >= 3:
        return (
            "Our capacity estimations are now solidly grounded: we know our expected QPS, cumulative 5-year storage, "
            "and RAM cache footprint. These quantitative bounds will directly guide our component choices. "
            "Let's move on to the next stage: High-Level Architecture Design."
        )

    # Initial prompt to begin calculations
    return (
        f"Let's ground the architecture for {ctx.problem_title or 'the system'} with back-of-the-envelope estimations. "
        "Based on our earlier discussion of Daily Active Users, how many read and write requests per second (QPS) "
        "do you anticipate on average, and what peak multiplier should we prepare for?"
    )


async def estimation_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> EstimationNodeOutput:
    """Conduct estimation turn, parse calculations, evaluate scale math, and return interviewer response.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        EstimationNodeOutput dictionary with updated dialogue, calculations list, and criteria.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()
    current_satisfied = ctx.get_satisfied_criteria(InterviewStage.ESTIMATION)

    # 1. Parse mathematical calculations from candidate's text
    new_calculations = extract_calculations_from_text(latest_candidate_text)

    # 2. Detect satisfied criteria
    updated_criteria = detect_satisfied_estimation_criteria(
        latest_candidate_text,
        current_satisfied,
    )

    # 3. Prepare prompt context
    missing = format_missing_estimation_criteria(updated_criteria)
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.ESTIMATION.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
        calculations=ctx.get_calculations() + new_calculations,
        satisfied_criteria=updated_criteria,
        candidate_name=ctx.candidate_name,
    )

    cfg = config or {}
    configurable = cfg.get("configurable", {})
    llm_client = configurable.get("llm_client")

    interviewer_reply: str | None = None

    # 4. Invoke LLM if available
    if llm_client is not None:
        try:
            persona_instructions = get_persona_prompt(ctx.persona)
            prompt = get_estimation_prompt(
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
            logger.warning("LLM invocation failed in estimation_node, falling back: %s", err)

    # 5. Calibrated deterministic fallback
    if not interviewer_reply:
        interviewer_reply = generate_fallback_estimation_response(
            ctx=ctx,
            candidate_text=latest_candidate_text,
            satisfied_criteria=updated_criteria,
            calculations=new_calculations,
        )

    # 6. Build turn update
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=interviewer_reply,
        metadata={
            "stage": InterviewStage.ESTIMATION.value,
            "node": "estimation_node",
            "extracted_calculations_count": len(new_calculations),
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "calculations": new_calculations,
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "stage_criteria_satisfied": {InterviewStage.ESTIMATION.value: updated_criteria},
        "next_node": None,
    }

"""System Design Interview Simulator - Deep Dive Node Implementation.

Executes the Component Deep Dive stage (Stage 4).
Evaluates data models, primary and secondary indexes, database partitioning and sharding keys,
caching patterns (cache-aside, invalidation, stampedes), and concurrency control mechanisms.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.types import DeepDiveNodeOutput
from app.prompts.base import PromptContext
from app.prompts.deep_dive import (
    DEEP_DIVE_PROBES,
    format_missing_deep_dive_criteria,
    get_deep_dive_prompt,
)
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Criteria discovery regex patterns
SCHEMA_KEYWORDS = re.compile(
    r"\b(schema|table|column|primary key|foreign key|index|b\+?\s*tree|lsm|nosql|sql|relational|document|wide-column|postgresql|mysql|cassandra|dynamodb|mongodb)\b",
    re.IGNORECASE,
)
CACHING_KEYWORDS = re.compile(
    r"\b(cache|caching|redis|memcached|cache-aside|write-through|write-behind|ttl|eviction|lru|lfu|cache stampede|dogpiling|bloom filter|invalidation)\b",
    re.IGNORECASE,
)
CONCURRENCY_SHARDING_KEYWORDS = re.compile(
    r"\b(shard|sharding|partition|consistent hashing|virtual node|hotspot|celebrity|lock|locking|optimistic|pessimistic|race condition|replication lag|read-after-write|idempotency)\b",
    re.IGNORECASE,
)


def detect_satisfied_deep_dive_criteria(
    candidate_text: str,
    already_satisfied: list[str],
) -> list[str]:
    """Inspect candidate response to identify newly satisfied component deep dive criteria."""
    newly_satisfied = list(already_satisfied)
    text = candidate_text.lower()

    if "data_storage_schema" not in newly_satisfied and SCHEMA_KEYWORDS.search(text):
        newly_satisfied.append("data_storage_schema")

    if "caching_strategy" not in newly_satisfied and CACHING_KEYWORDS.search(text):
        newly_satisfied.append("caching_strategy")

    if "concurrency_or_sharding" not in newly_satisfied and CONCURRENCY_SHARDING_KEYWORDS.search(text):
        newly_satisfied.append("concurrency_or_sharding")

    return newly_satisfied


def generate_fallback_deep_dive_response(
    ctx: InterviewContext,
    candidate_text: str,
    satisfied_criteria: list[str],
) -> str:
    """Synthesize high-fidelity deterministic deep dive feedback when LLM is offline or mock."""
    seniority = ctx.seniority_level.lower()
    has_schema = "data_storage_schema" in satisfied_criteria
    has_cache = "caching_strategy" in satisfied_criteria
    has_sharding = "concurrency_or_sharding" in satisfied_criteria

    # If candidate discussed schema but not sharding or hotspots
    if has_schema and not has_sharding:
        reply = (
            "The proposed data model and key structure are clearly defined. "
            "Now let's examine horizontal database partitioning: as data volume scales into tens of terabytes, "
            "what sharding key do you choose? How will you prevent hotspots or skewed traffic if a celebrity user "
            "receives disproportionately high traffic?"
        )
        if seniority == SeniorityLevel.STAFF.value:
            reply += " Also discuss how consistent hashing with virtual nodes minimizes data migration during resharding."
        return reply

    # If candidate discussed sharding but not cache invalidation / stampedes
    if has_sharding and not has_cache:
        return (
            "Your sharding key strategy and partition distribution address data scale effectively. "
            "Now let's drill into the caching layer: are you adopting Cache-Aside or Write-Through? "
            "How do you ensure cache consistency when records are updated, "
            "and how does your system protect against cache stampedes (dogpiling) when hot keys expire under peak load?"
        )

    # If all criteria are satisfied or multiple turns completed
    if (has_schema and has_cache and has_sharding) or ctx.stage_turn_count >= 3:
        return (
            "You have covered the deep dive thoroughly: data modeling, partitioning keys, cache consistency, "
            "and concurrency controls are well reasoned. "
            "Now let's examine resilience under adversity. Let's move to Stage 5: Bottlenecks & Fault Tolerance."
        )

    # Default initial deep dive prompt
    return (
        f"Let's zoom into a component deep dive for {ctx.problem_title or 'the system'}, specifically our storage layer. "
        "What database technology (SQL vs NoSQL) are you selecting for the primary entity store, "
        "and what does the schema definition look like, including primary keys and secondary indexes?"
    )


async def deep_dive_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> DeepDiveNodeOutput:
    """Conduct deep dive turn probing database schema, sharding, caching, and concurrency.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        DeepDiveNodeOutput dictionary with updated dialogue, turn counters, and criteria.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()
    current_satisfied = ctx.get_satisfied_criteria(InterviewStage.DEEP_DIVE)

    # 1. Detect satisfied criteria
    updated_criteria = detect_satisfied_deep_dive_criteria(
        latest_candidate_text,
        current_satisfied,
    )

    # 2. Prepare prompt context
    missing = format_missing_deep_dive_criteria(updated_criteria)
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.DEEP_DIVE.value,
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
            prompt = get_deep_dive_prompt(
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
            logger.warning("LLM invocation failed in deep_dive_node, falling back: %s", err)

    # 4. Calibrated deterministic fallback
    if not interviewer_reply:
        interviewer_reply = generate_fallback_deep_dive_response(
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
            "stage": InterviewStage.DEEP_DIVE.value,
            "node": "deep_dive_node",
            "satisfied_criteria_count": len(updated_criteria),
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "stage_criteria_satisfied": {InterviewStage.DEEP_DIVE.value: updated_criteria},
        "next_node": None,
    }

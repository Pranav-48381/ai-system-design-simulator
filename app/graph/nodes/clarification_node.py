"""System Design Interview Simulator - Clarification Node Implementation.

Executes the Clarification & Requirements discovery stage (Stage 1).
Assesses the candidate's ability to formulate functional requirements, scope system
boundaries, probe non-functional SLAs/SLOs, and uncover traffic scale targets.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.types import ClarificationNodeOutput
from app.prompts.base import PromptContext
from app.prompts.clarification import (
    CLARIFICATION_PROBES,
    format_missing_clarification_criteria,
    get_clarification_prompt,
)
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Heuristics for discovering satisfied criteria in candidate responses
FUNCTIONAL_KEYWORDS = re.compile(
    r"\b(feature|functional|user can|users can|endpoint|action|shorten|redirect|send message|stream|upload|download|view|search|post|feed)\b",
    re.IGNORECASE,
)
NON_FUNCTIONAL_KEYWORDS = re.compile(
    r"\b(latency|availability|consistency|sla|slo|p99|p95|ms|millisecond|uptime|fault tolerance|durability|cap theorem|partition tolerance)\b",
    re.IGNORECASE,
)
SCALE_KEYWORDS = re.compile(
    r"\b(scale|dau|mau|qps|tps|read ratio|write ratio|traffic|users|requests per second|retention|storage)\b",
    re.IGNORECASE,
)


def detect_satisfied_clarification_criteria(
    candidate_text: str,
    already_satisfied: list[str],
) -> list[str]:
    """Inspect candidate input to identify newly fulfilled clarification criteria."""
    newly_satisfied = list(already_satisfied)
    text = candidate_text.lower()

    if "functional_requirements" not in newly_satisfied and FUNCTIONAL_KEYWORDS.search(text):
        newly_satisfied.append("functional_requirements")

    if "non_functional_requirements" not in newly_satisfied and NON_FUNCTIONAL_KEYWORDS.search(text):
        newly_satisfied.append("non_functional_requirements")

    if "scale_assumptions" not in newly_satisfied and SCALE_KEYWORDS.search(text):
        newly_satisfied.append("scale_assumptions")

    return newly_satisfied


def generate_fallback_clarification_response(
    ctx: InterviewContext,
    candidate_text: str,
    satisfied_criteria: list[str],
) -> str:
    """Synthesize high-fidelity, deterministic interviewer feedback when LLM is offline or mock.

    Calibrated according to interviewer persona and candidate seniority level.
    """
    problem_title = ctx.problem_title or "this system"
    scale_dict = ctx.problem_scale or {}
    dau = scale_dict.get("dau", "50 million Daily Active Users (DAU)")
    read_write = scale_dict.get("read_write_ratio", "100:1 read-to-write ratio")
    seniority = ctx.seniority_level.lower()

    # If candidate asked questions about scale or traffic
    if SCALE_KEYWORDS.search(candidate_text):
        response = (
            f"Good question regarding scale for {problem_title}. We can assume approximately {dau}, "
            f"with an anticipated {read_write}. "
            "How would this traffic pattern impact your choice between prioritizing read latency versus write throughput?"
        )
        if seniority == SeniorityLevel.STAFF.value:
            response += " Also, consider whether we need global multi-region active-active deployment or single-region with read replicas."
        return response

    # If candidate discussed non-functional SLOs
    if NON_FUNCTIONAL_KEYWORDS.search(candidate_text):
        return (
            f"Those latency and availability targets are well reasoned for {problem_title}. "
            "P99 read latency under 100ms with 99.99% availability makes sense for our user experience. "
            "Are there any specific data consistency requirements (e.g. strict linearizability vs eventual consistency) "
            "we should enforce across replicas?"
        )

    # If all primary criteria satisfied, suggest stage advance
    if len(satisfied_criteria) >= 3 or ctx.stage_turn_count >= 3:
        return (
            f"We have established clear functional requirements, traffic scale ({dau}), and availability SLOs for {problem_title}. "
            "The scope is well defined. Let's move on to the next stage: Back-of-the-envelope Capacity Estimation."
        )

    # Default initial / intermediate requirements probing
    return (
        f"Thanks for setting the initial direction for {problem_title}. "
        "To ensure we stay focused on the core problem within our time limit, "
        "what are the top 2 or 3 core functional features we should prioritize for the MVP, "
        "and what features should we explicitly consider out-of-scope?"
    )


async def clarification_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> ClarificationNodeOutput:
    """Conduct clarification turn, evaluate criteria progress, and return interviewer response.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        ClarificationNodeOutput dictionary with updated dialogue, turn counters, and criteria.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()
    current_satisfied = ctx.get_satisfied_criteria(InterviewStage.CLARIFICATION)

    # 1. Detect criteria satisfied from candidate's latest response
    updated_criteria = detect_satisfied_clarification_criteria(
        latest_candidate_text,
        current_satisfied,
    )

    # 2. Prepare prompt context
    missing = format_missing_clarification_criteria(updated_criteria)
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.CLARIFICATION.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
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
            prompt = get_clarification_prompt(
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
            logger.warning("LLM invocation failed in clarification_node, falling back: %s", err)

    # 4. Fall back to calibrated deterministic response if LLM omitted or failed
    if not interviewer_reply:
        interviewer_reply = generate_fallback_clarification_response(
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
            "stage": InterviewStage.CLARIFICATION.value,
            "node": "clarification_node",
            "satisfied_criteria_count": len(updated_criteria),
        },
        increment_counts=True,
    )

    # 6. Compose stage summary notes if criteria satisfied
    summary_notes: dict[str, str] = {}
    if len(updated_criteria) >= 2:
        summary_notes[InterviewStage.CLARIFICATION.value] = (
            f"Candidate clarified {len(updated_criteria)} core criteria: {', '.join(updated_criteria)}."
        )

    return {
        "messages": turn_update["messages"],
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "stage_criteria_satisfied": {InterviewStage.CLARIFICATION.value: updated_criteria},
        "stage_summary_notes": summary_notes,
        "next_node": None,
    }

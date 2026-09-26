"""System Design Interview Simulator - Architecture Node Implementation.

Executes the High-Level Architecture Design stage (Stage 3).
Evaluates the candidate's component decomposition, client-to-backend ingress paths,
API contracts, asynchronous message queues, and whiteboard diagram representations.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.types import ArchitectureNodeOutput
from app.prompts.architecture import (
    ARCHITECTURE_PROBES,
    format_missing_architecture_criteria,
    get_architecture_prompt,
)
from app.prompts.base import PromptContext
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Heuristics for detecting Mermaid or ASCII architecture blocks
MERMAID_BLOCK_REGEX = re.compile(
    r"```(?:mermaid)?\s*([\s\S]*?)```",
    re.IGNORECASE,
)
MERMAID_HEADER_REGEX = re.compile(
    r"\b(graph (?:TD|LR|TB|RL)|flowchart (?:TD|LR|TB|RL))\b",
    re.IGNORECASE,
)

# Criteria discovery keywords
API_KEYWORDS = re.compile(
    r"\b(POST|GET|PUT|DELETE|PATCH|endpoint|api|route|payload|status code|200 ok|201 created|json response)\b",
    re.IGNORECASE,
)
COMPONENT_KEYWORDS = re.compile(
    r"\b(load balancer|api gateway|reverse proxy|service|worker|microservice|kafka|rabbitmq|sqs|redis|cache|postgres|cassandra|database)\b",
    re.IGNORECASE,
)
DATA_FLOW_KEYWORDS = re.compile(
    r"(-->|->|data flow|read path|write path|ingress|pub/sub|asynchronous|event-driven|pipeline)\b",
    re.IGNORECASE,
)


def extract_mermaid_diagram(text: str) -> str | None:
    """Extract raw Mermaid diagram syntax from markdown code blocks or raw text."""
    # Check for fenced code block first
    match = MERMAID_BLOCK_REGEX.search(text)
    if match:
        content = match.group(1).strip()
        if MERMAID_HEADER_REGEX.search(content) or "-->" in content:
            return content

    # Check for inline flowchart/graph definition
    if MERMAID_HEADER_REGEX.search(text):
        lines = [line for line in text.splitlines() if line.strip()]
        diagram_lines = []
        capturing = False
        for line in lines:
            if MERMAID_HEADER_REGEX.search(line):
                capturing = True
            if capturing:
                if line.startswith("```") and diagram_lines:
                    break
                diagram_lines.append(line)
        if diagram_lines:
            return "\n".join(diagram_lines)

    return None


def detect_satisfied_architecture_criteria(
    candidate_text: str,
    already_satisfied: list[str],
    has_diagram: bool,
) -> list[str]:
    """Inspect candidate response to identify newly satisfied high-level architecture criteria."""
    newly_satisfied = list(already_satisfied)
    text = candidate_text.lower()

    if "api_endpoints" not in newly_satisfied and API_KEYWORDS.search(text):
        newly_satisfied.append("api_endpoints")

    if "core_components" not in newly_satisfied and (COMPONENT_KEYWORDS.search(text) or has_diagram):
        newly_satisfied.append("core_components")

    if "high_level_data_flow" not in newly_satisfied and (DATA_FLOW_KEYWORDS.search(text) or has_diagram):
        newly_satisfied.append("high_level_data_flow")

    return newly_satisfied


def generate_fallback_architecture_response(
    ctx: InterviewContext,
    candidate_text: str,
    satisfied_criteria: list[str],
    has_diagram: bool,
) -> str:
    """Synthesize high-fidelity deterministic architecture feedback when LLM is offline or mock."""
    seniority = ctx.seniority_level.lower()
    has_api = "api_endpoints" in satisfied_criteria
    has_components = "core_components" in satisfied_criteria
    has_flow = "high_level_data_flow" in satisfied_criteria

    # If candidate provided diagram
    if has_diagram:
        return (
            "The architecture diagram provides a clean high-level topology. "
            "I see the separation between your ingress gateway, application services, and persistence stores. "
            "How do your application servers handle asynchronous tasks or heavy background processing—"
            "do they push events to a message queue like Kafka or SQS to keep user-facing API latencies low?"
        )

    # If candidate discussed APIs but not data flow or queuing
    if has_api and not has_flow:
        return (
            "Those API contracts are clean and RESTful. "
            "Now let's trace the end-to-end data flow: when a write request hits the API Gateway, "
            "can you walk me through the step-by-step path down to storage? "
            "What happens if downstream persistence experiences a sudden latency spike?"
        )

    # If candidate satisfied all primary criteria or completed several turns
    if (has_api and has_components and has_flow) or ctx.stage_turn_count >= 3:
        return (
            "The macro architecture is well articulated: client ingress, stateless service tier, "
            "asynchronous event queues, and storage boundaries are clearly decoupled. "
            "Now let's zoom in on the most critical subsystems. Let's move to Stage 4: Component Deep Dive."
        )

    # Default initial architecture prompt
    return (
        f"Now let's design the high-level architecture for {ctx.problem_title or 'the system'}. "
        "Can you outline the core functional components (API Gateway, application services, databases, queues) "
        "and define the primary API endpoints our clients will call?"
    )


async def architecture_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> ArchitectureNodeOutput:
    """Review candidate's high-level architecture, parse diagrams, and generate feedback.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        ArchitectureNodeOutput dictionary with updated dialogue, artifacts, and criteria.
    """
    ctx = InterviewContext(state)
    latest_candidate_text = ctx.get_latest_candidate_text()
    current_satisfied = ctx.get_satisfied_criteria(InterviewStage.ARCHITECTURE)

    # 1. Parse architecture diagram / Mermaid representation if provided
    diagram_content = extract_mermaid_diagram(latest_candidate_text)
    has_diagram = diagram_content is not None

    artifacts_update: dict[str, Any] = {}
    history_update: list[dict[str, Any]] = []

    if diagram_content:
        diagram_artifact = {
            "type": "architecture_diagram",
            "format": "mermaid",
            "content": diagram_content,
            "version": len(state.get("artifact_history", [])) + 1,
            "updated_at": time.time(),
        }
        artifacts_update["architecture_diagram"] = diagram_artifact
        history_update.append(diagram_artifact)

    # 2. Detect satisfied criteria
    updated_criteria = detect_satisfied_architecture_criteria(
        latest_candidate_text,
        current_satisfied,
        has_diagram=has_diagram,
    )

    # 3. Prepare prompt context
    missing = format_missing_architecture_criteria(updated_criteria)
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.ARCHITECTURE.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
        artifacts={**state.get("active_artifacts", {}), **artifacts_update},
        calculations=ctx.get_calculations(),
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
            prompt = get_architecture_prompt(
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
            logger.warning("LLM invocation failed in architecture_node, falling back: %s", err)

    # 5. Calibrated deterministic fallback
    if not interviewer_reply:
        interviewer_reply = generate_fallback_architecture_response(
            ctx=ctx,
            candidate_text=latest_candidate_text,
            satisfied_criteria=updated_criteria,
            has_diagram=has_diagram,
        )

    # 6. Build turn update
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=interviewer_reply,
        metadata={
            "stage": InterviewStage.ARCHITECTURE.value,
            "node": "architecture_node",
            "has_diagram_update": has_diagram,
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "active_artifacts": artifacts_update,
        "artifact_history": history_update,
        "stage_turn_count": turn_update["stage_turn_count"],
        "total_turn_count": turn_update["total_turn_count"],
        "stage_criteria_satisfied": {InterviewStage.ARCHITECTURE.value: updated_criteria},
        "next_node": None,
    }

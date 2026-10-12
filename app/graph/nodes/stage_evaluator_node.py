"""System Design Interview Simulator - Stage Evaluator Node Implementation.

Executes intermediate stage assessment and stage transition gating.
Summarizes candidate accomplishments for the completed stage, verifies prerequisites,
updates stage progress records, and smoothly transitions to the next interview stage.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import (
    INTERVIEW_STAGE_TITLES,
    InterviewStage,
    SpeakerRole,
)
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.stages import get_next_stage, get_stage_definition
from app.graph.state import InterviewState
from app.graph.types import GraphNodeName, StageEvaluatorNodeOutput
from app.prompts.base import PromptContext
from app.prompts.personas import get_persona_prompt

logger = logging.getLogger(__name__)

# Canonical map from stage to primary probing node
STAGE_NODE_MAP: dict[InterviewStage, str] = {
    InterviewStage.CLARIFICATION: GraphNodeName.CLARIFICATION.value,
    InterviewStage.ESTIMATION: GraphNodeName.ESTIMATION.value,
    InterviewStage.ARCHITECTURE: GraphNodeName.ARCHITECTURE.value,
    InterviewStage.DEEP_DIVE: GraphNodeName.DEEP_DIVE.value,
    InterviewStage.BOTTLENECK: GraphNodeName.BOTTLENECK.value,
    InterviewStage.EVALUATION: GraphNodeName.FINAL_EVALUATOR.value,
}

# Stage transition conversational announcements
STAGE_TRANSITION_MESSAGES: dict[InterviewStage, str] = {
    InterviewStage.ESTIMATION: (
        "We have established clear problem scope, functional requirements, and non-functional SLOs. "
        "Now let's move into Stage 2: Capacity Estimation & Scale Calculations. "
        "Based on our target user scale, what are our expected read and write throughput (QPS), "
        "and how much storage will the system consume over time?"
    ),
    InterviewStage.ARCHITECTURE: (
        "Your quantitative capacity numbers give us solid architectural boundaries. "
        "Let's proceed to Stage 3: High-Level Architecture & API Design. "
        "How would you structure the core services, API contracts, and request data flow from client ingress to persistence?"
    ),
    InterviewStage.DEEP_DIVE: (
        "The high-level architecture and API design are well mapped out. "
        "Let's move into Stage 4: Component Deep Dive. "
        "Let's zoom into our data tier and caching: what specific schema, indexing strategy, "
        "and partitioning keys do you propose to support this scale?"
    ),
    InterviewStage.BOTTLENECK: (
        "The data models, sharding strategy, and cache invalidation mechanics are solid. "
        "Now let's stress-test the design in Stage 5: Bottlenecks & Resilience. "
        "Where are the single points of failure in your architecture, and how do we prevent cascading outages?"
    ),
    InterviewStage.EVALUATION: (
        "We have thoroughly stress-tested the resilience, scalability, and trade-offs of your design. "
        "That concludes our technical design phases! Let's proceed to our final Evaluation & Debrief stage."
    ),
}


def build_stage_summary_note(
    stage: InterviewStage,
    satisfied_criteria: list[str],
    turn_count: int,
) -> str:
    """Compose concise technical summary notes for a completed stage."""
    title = INTERVIEW_STAGE_TITLES.get(stage, stage.value)
    criteria_count = len(satisfied_criteria)
    criteria_list = ", ".join(satisfied_criteria) if satisfied_criteria else "baseline discussion"
    return (
        f"Completed {title} in {turn_count} dialogue turns. "
        f"Addressed {criteria_count} core criteria ({criteria_list})."
    )


async def stage_evaluator_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> StageEvaluatorNodeOutput:
    """Evaluate completed stage, compile stage summary, and advance to next stage.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        StageEvaluatorNodeOutput dictionary updating current_stage, completed_stages,
        summary notes, and routing markers.
    """
    ctx = InterviewContext(state)
    current_stage = ctx.current_stage
    satisfied = ctx.get_satisfied_criteria(current_stage)
    stage_turns = ctx.stage_turn_count

    # 1. Compile stage summary note
    summary_note = build_stage_summary_note(
        stage=current_stage,
        satisfied_criteria=satisfied,
        turn_count=stage_turns,
    )
    logger.info("Stage evaluated: %s -> %s", current_stage.value, summary_note)

    # 2. Determine successor stage
    next_stage = get_next_stage(current_stage)
    if next_stage is None or next_stage == InterviewStage.EVALUATION:
        destination_stage = InterviewStage.EVALUATION
        next_node = GraphNodeName.FINAL_EVALUATOR.value
    else:
        destination_stage = next_stage
        next_node = STAGE_NODE_MAP.get(next_stage, GraphNodeName.ARCHITECTURE.value)

    # 3. Formulate transition message
    transition_text = STAGE_TRANSITION_MESSAGES.get(
        destination_stage,
        f"Let's proceed to the next stage: {INTERVIEW_STAGE_TITLES.get(destination_stage, destination_stage.value)}.",
    )

    # 4. Append interviewer transition turn
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=transition_text,
        metadata={
            "stage": destination_stage.value,
            "node": "stage_evaluator_node",
            "previous_stage": current_stage.value,
            "stage_transition": True,
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "current_stage": destination_stage.value,
        "completed_stages": [current_stage.value],
        "stage_turn_count": 0,
        "total_turn_count": turn_update["total_turn_count"],
        "stage_summary_notes": {current_stage.value: summary_note},
        "is_stage_complete": True,
        "next_node": next_node,
    }

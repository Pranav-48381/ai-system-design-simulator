"""System Design Interview Simulator - Router Node Implementation.

Analyzes candidate input using LLM intent classification and fallback heuristic extraction,
evaluates stage entry/exit guards, checks transition readiness, and dynamically directs
the LangGraph StateGraph execution to the appropriate stage or utility node.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.core.constants import InterviewStage
from app.graph.context import InterviewContext
from app.graph.guards import evaluate_stage_exit_guards
from app.graph.stages import get_next_stage
from app.graph.state import InterviewState
from app.graph.types import (
    CandidateAction,
    CandidateIntentClassification,
    GraphNodeName,
    RouterNodeOutput,
)
from app.prompts.router import (
    get_router_intent_prompt,
    get_stage_readiness_prompt,
)

logger = logging.getLogger(__name__)

# Heuristic patterns for robust fallback classification when LLM is offline or mock
HINT_PATTERN = re.compile(
    r"\b(hint|clue|stuck|lost|don['’]?t know|give me a tip|guidance|nudge|help me with)\b",
    re.IGNORECASE,
)
STAGE_ADVANCE_PATTERN = re.compile(
    r"\b(next stage|move on|advance|ready to move|finished with|conclude requirements|proceed to|done with)\b",
    re.IGNORECASE,
)
ESTIMATION_PATTERN = re.compile(
    r"(\b(qps|tps|iops|dau|mau|bytes|gb|tb|pb|read ratio|write ratio|queries per second|throughput)\b|\d+\s*(gb|tb|mb|kb|sec|qps|bytes))",
    re.IGNORECASE,
)
CANVAS_PATTERN = re.compile(
    r"(\b(mermaid|flowchart|graph lr|graph td|architecture diagram|client\s*-->|component diagram)\b|```mermaid)",
    re.IGNORECASE,
)
QUESTION_PATTERN = re.compile(
    r"(\?|\b(should we|can we assume|do we need|is it required|what is the expected|who are the users)\b)",
    re.IGNORECASE,
)


def classify_candidate_intent_heuristically(
    message: str,
    current_stage: str,
) -> CandidateIntentClassification:
    """Classify candidate intent via deterministic regex pattern heuristics.

    Acts as a high-speed, zero-cost fallback and offline classifier.

    Args:
        message: Raw message text submitted by the candidate.
        current_stage: Name of active interview stage.

    Returns:
        Structured CandidateIntentClassification instance.
    """
    clean_msg = message.strip()
    if not clean_msg:
        return CandidateIntentClassification(
            action=CandidateAction.RESPOND,
            confidence=0.5,
            reasoning="Empty candidate message; default to respond.",
        )

    # 1. Hint requests
    if HINT_PATTERN.search(clean_msg):
        return CandidateIntentClassification(
            action=CandidateAction.REQUEST_HINT,
            confidence=0.92,
            reasoning="Candidate explicitly mentioned needing a hint or feeling stuck.",
            extracted_entities={"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": False},
        )

    # 2. Stage advancement requests
    if STAGE_ADVANCE_PATTERN.search(clean_msg):
        return CandidateIntentClassification(
            action=CandidateAction.SUBMIT_STAGE,
            confidence=0.90,
            reasoning="Candidate requested advancing or moving to the next stage.",
            extracted_entities={"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": True},
        )

    # 3. Canvas & diagram updates
    if CANVAS_PATTERN.search(clean_msg):
        return CandidateIntentClassification(
            action=CandidateAction.UPDATE_CANVAS,
            confidence=0.95,
            reasoning="Candidate provided diagram or canvas syntax.",
            extracted_entities={"is_quantitative": False, "contains_diagram": True, "explicit_stage_request": False},
        )

    # 4. Quantitative capacity estimations
    if ESTIMATION_PATTERN.search(clean_msg):
        return CandidateIntentClassification(
            action=CandidateAction.SUBMIT_ESTIMATION,
            confidence=0.88,
            reasoning="Candidate submitted quantitative traffic, storage, or memory calculations.",
            extracted_entities={"is_quantitative": True, "contains_diagram": False, "explicit_stage_request": False},
        )

    # 5. Clarifying questions
    if QUESTION_PATTERN.search(clean_msg):
        return CandidateIntentClassification(
            action=CandidateAction.ASK_QUESTION,
            confidence=0.85,
            reasoning="Candidate asked a question about scope, requirements, or constraints.",
            extracted_entities={"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": False},
        )

    # Default to direct response / technical explanation
    return CandidateIntentClassification(
        action=CandidateAction.RESPOND,
        confidence=0.80,
        reasoning="Candidate is responding to interviewer prompt or describing architecture.",
        extracted_entities={"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": False},
    )


def map_stage_to_node_name(stage: InterviewStage | str) -> str:
    """Map interview stage enum or string to canonical LangGraph StateGraph node name."""
    stage_val = stage.value if isinstance(stage, InterviewStage) else str(stage).lower()
    mapping: dict[str, str] = {
        InterviewStage.CLARIFICATION.value: GraphNodeName.CLARIFICATION.value,
        InterviewStage.ESTIMATION.value: GraphNodeName.ESTIMATION.value,
        InterviewStage.ARCHITECTURE.value: GraphNodeName.ARCHITECTURE.value,
        InterviewStage.DEEP_DIVE.value: GraphNodeName.DEEP_DIVE.value,
        InterviewStage.BOTTLENECK.value: GraphNodeName.BOTTLENECK.value,
        InterviewStage.EVALUATION.value: GraphNodeName.FINAL_EVALUATOR.value,
    }
    return mapping.get(stage_val, GraphNodeName.CLARIFICATION.value)


async def router_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> RouterNodeOutput:
    """Evaluate candidate input, classify intent, check stage exit guards, and route graph.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time settings or LLM client.

    Returns:
        RouterNodeOutput dictionary specifying candidate_intent and next_node.
    """
    ctx = InterviewContext(state)
    current_stage_enum = ctx.current_stage
    latest_candidate_text = ctx.get_latest_candidate_text()

    cfg = config or {}
    configurable = cfg.get("configurable", {})
    llm_client = configurable.get("llm_client")

    intent_classification: CandidateIntentClassification | None = None

    # Step 1: Attempt LLM-based intent classification if client is configured
    if llm_client is not None and latest_candidate_text:
        try:
            recent_turns = ctx.format_recent_dialogue(max_turns=4)
            dialogue_str = "\n".join(f"{t['role'].capitalize()}: {t['content']}" for t in recent_turns)
            prompt = get_router_intent_prompt(
                candidate_message=latest_candidate_text,
                current_stage=current_stage_enum.value,
                dialogue_context=dialogue_str,
            )

            response = None
            if hasattr(llm_client, "ainvoke"):
                response = await llm_client.ainvoke(prompt)
            elif hasattr(llm_client, "invoke"):
                response = llm_client.invoke(prompt)

            if response is not None:
                content = getattr(response, "content", str(response)).strip()
                # Parse JSON payload from response
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    action_str = parsed.get("action", CandidateAction.RESPOND.value)
                    intent_classification = CandidateIntentClassification(
                        action=CandidateAction(action_str) if action_str in CandidateAction._value2member_map_ else CandidateAction.RESPOND,
                        confidence=float(parsed.get("confidence", 0.9)),
                        target_stage=InterviewStage(parsed["target_stage"]) if parsed.get("target_stage") in InterviewStage._value2member_map_ else None,
                        extracted_entities=parsed.get("extracted_entities", {}),
                        reasoning=parsed.get("reasoning", "LLM classified intent."),
                    )
        except Exception as err:
            logger.warning("LLM router classification failed, falling back to heuristics: %s", err)

    # Step 2: Fall back to deterministic heuristic classification if LLM omitted or failed
    if intent_classification is None:
        intent_classification = classify_candidate_intent_heuristically(
            latest_candidate_text,
            current_stage_enum.value,
        )

    action = intent_classification.action

    # Step 3: Determine destination node based on intent and stage guards
    next_node: str

    if action == CandidateAction.REQUEST_HINT:
        # Route to hint generator node
        next_node = GraphNodeName.HINT_GENERATOR.value

    elif action in (CandidateAction.SUBMIT_STAGE, CandidateAction.SKIP_STAGE):
        # Evaluate whether candidate has satisfied exit criteria or if force transition is needed
        force = (action == CandidateAction.SKIP_STAGE)
        guard_result = evaluate_stage_exit_guards(state, force_transition=force)

        if guard_result.can_exit:
            # Stage successfully satisfied; route to stage evaluator for assessment
            if current_stage_enum == InterviewStage.BOTTLENECK:
                next_node = GraphNodeName.FINAL_EVALUATOR.value
            else:
                next_node = GraphNodeName.STAGE_EVALUATOR.value
        else:
            # Stage criteria not met; candidate remains in current stage with constructive probing
            logger.info(
                "Candidate requested stage advance but exit guards rejected: %s. Remaining in %s.",
                guard_result.reason,
                current_stage_enum.value,
            )
            next_node = map_stage_to_node_name(current_stage_enum)

    elif action == CandidateAction.UPDATE_CANVAS:
        # Route directly to architecture node to update whiteboard
        next_node = GraphNodeName.ARCHITECTURE.value

    else:
        # Standard conversation turn (respond, ask_question, submit_estimation, etc.)
        # If candidate submitted estimation during estimation stage, route to estimation node
        # Otherwise route to active stage handler
        next_node = map_stage_to_node_name(current_stage_enum)

    return {
        "candidate_intent": action.value,
        "next_node": next_node,
        "error": None,
    }

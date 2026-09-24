"""System Design Interview Simulator - Intent Classification & Router Prompt Templates.

Implements system prompt templates, few-shot classification examples, and stage transition
readiness evaluation directives for the LangGraph state machine router node.
Enables accurate extraction of candidate intent, stage advancement requests, hints, and canvas updates.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.constants import InterviewStage
from app.graph.types import CandidateAction

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Intent Classification Prompt Foundation
# -----------------------------------------------------------------------------

ROUTER_INTENT_SYSTEM_PROMPT = """You are an expert NLP dialogue router for an AI Technical System Design Interview platform.
Your task is to analyze the candidate's latest message within the context of the ongoing interview turn
and classify their primary intent into exactly one of the supported CandidateAction categories.

SUPPORTED CANDIDATE ACTION CATEGORIES:
1. "respond": The candidate is answering an interviewer question, elaborating on their architecture, or discussing technical trade-offs.
2. "ask_question": The candidate is asking the interviewer a clarifying question about requirements, scope, traffic scale, or constraints.
3. "submit_estimation": The candidate is presenting quantitative capacity calculations (QPS, storage, bandwidth, memory/cache math).
4. "update_canvas": The candidate is providing whiteboard diagram syntax (e.g. Mermaid, ASCII architecture blocks) or component lists.
5. "request_hint": The candidate is explicitly stuck and requesting guidance, a hint, or direction ("I'm not sure how to partition this, can you give me a hint?").
6. "submit_stage": The candidate is declaring they have finished the current stage and proactively asking to move to the next stage ("I think we covered requirements, can we move to estimation?").
7. "concur_or_modify": The candidate is acknowledging an interviewer suggestion, agreeing with feedback, or accepting a proposed course correction.
8. "skip_stage": The candidate is requesting to bypass or skip the current stage.
9. "general_query": Meta-inquiries about interview pacing, time remaining, or unrelated conversational remarks.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding conversational prose or markdown formatting outside the JSON code block.
The JSON must follow this exact schema:
{
  "action": "<one of the 9 action categories listed above>",
  "confidence": <float between 0.0 and 1.0>,
  "target_stage": "<optional target interview stage name if candidate requested a transition, else null>",
  "reasoning": "<concise 1-sentence justification for this classification>",
  "extracted_entities": {
    "is_quantitative": <boolean>,
    "contains_diagram": <boolean>,
    "explicit_stage_request": <boolean>
  }
}
"""

ROUTER_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "input": "Can we assume 50 million Daily Active Users, and do we need to support image uploads or just text links?",
        "output": {
            "action": "ask_question",
            "confidence": 0.98,
            "target_stage": None,
            "reasoning": "Candidate is clarifying scale assumptions and functional scope boundaries.",
            "extracted_entities": {"is_quantitative": True, "contains_diagram": False, "explicit_stage_request": False},
        },
    },
    {
        "input": "With 100M daily writes of 500 bytes each, that is 50 GB per day. Over 5 years with 3x replication, we need about 270 TB.",
        "output": {
            "action": "submit_estimation",
            "confidence": 0.99,
            "target_stage": None,
            "reasoning": "Candidate is performing capacity storage and replication calculations.",
            "extracted_entities": {"is_quantitative": True, "contains_diagram": False, "explicit_stage_request": False},
        },
    },
    {
        "input": "I have documented the core requirements and scale. Can we proceed to the high-level architecture?",
        "output": {
            "action": "submit_stage",
            "confidence": 0.95,
            "target_stage": "architecture",
            "reasoning": "Candidate is explicitly requesting to advance from current stage to architecture.",
            "extracted_entities": {"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": True},
        },
    },
    {
        "input": "I'm a bit stuck on how to handle cache stampedes when hot keys expire. Any recommendations or hints?",
        "output": {
            "action": "request_hint",
            "confidence": 0.97,
            "target_stage": None,
            "reasoning": "Candidate is explicitly acknowledging being blocked and asking for a hint.",
            "extracted_entities": {"is_quantitative": False, "contains_diagram": False, "explicit_stage_request": False},
        },
    },
]

# -----------------------------------------------------------------------------
# Stage Readiness Evaluation Prompt Foundation
# -----------------------------------------------------------------------------

STAGE_READINESS_SYSTEM_PROMPT = """You are an objective Stage Transition Gatekeeper for an AI Technical System Design Interview platform.
Your responsibility is to evaluate whether the candidate has adequately satisfied the foundational requirements of the current stage
before allowing the interview state machine to transition to the successor stage.

EVALUATION CRITERIA:
1. Has the candidate addressed the essential core competencies of the stage?
   - Clarification: Functional requirements (2-3), non-functional constraints (latency, availability), and scope boundaries.
   - Estimation: QPS (read/write), multi-year storage volume, and cache/memory sizing.
   - Architecture: Client ingress, stateless app servers, API contracts, async queuing, and persistence stores.
   - Deep Dive: Data schemas/keys, SQL vs NoSQL justification, sharding strategy, and cache invalidation.
   - Bottlenecks: SPOF identification, cascading failure protection (circuit breakers/bulkheads), and rate limiting.

2. Pacing & Turn Thresholds:
   - Ensure the stage has not been cut short prematurely (has at least reached minimum turn threshold).
   - If the candidate attempts to skip ahead without answering fundamental questions, reject the transition with constructive guidance.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding markdown formatting outside the JSON code block.
Schema:
{
  "can_transition": <boolean>,
  "from_stage": "<current_stage>",
  "to_stage": "<target_stage>",
  "reason": "<clear explanation for allowing or deferring transition>",
  "missing_criteria": ["<list of essential criteria still missing, if any>"],
  "recommended_action": "<'advance' | 'continue' | 'nudge_missing_criteria'>"
}
"""


def get_router_intent_prompt(
    candidate_message: str,
    current_stage: str,
    dialogue_context: str = "",
) -> str:
    """Compose intent classification prompt with few-shot examples and current turn context.

    Args:
        candidate_message: Latest raw message text from candidate.
        current_stage: Identifier of active interview stage.
        dialogue_context: Recent dialogue transcript snippet for context.

    Returns:
        Fully compiled user prompt for router intent classification.
    """
    examples_str = json.dumps(ROUTER_FEW_SHOT_EXAMPLES, indent=2)

    return f"""{ROUTER_INTENT_SYSTEM_PROMPT}

FEW-SHOT REFERENCE EXAMPLES:
{examples_str}

================================================================================
CURRENT TURN CONTEXT
================================================================================
Active Interview Stage: {current_stage.upper()}

Recent Dialogue Context:
{dialogue_context if dialogue_context.strip() else "[Turn 1 - Interview start]"}

Candidate's Latest Message:
\"\"\"{candidate_message.strip()}\"\"\"

Classify the candidate's intent according to the schema above:"""


def get_stage_readiness_prompt(
    current_stage: str,
    next_stage: str,
    satisfied_criteria: list[str],
    dialogue_history: str = "",
    artifacts_summary: str = "",
    turn_count: int = 0,
) -> str:
    """Compose stage transition readiness evaluation prompt.

    Args:
        current_stage: Active interview stage identifier.
        next_stage: Proposed destination interview stage identifier.
        satisfied_criteria: List of criteria already recorded as satisfied.
        dialogue_history: Recent conversation history in the current stage.
        artifacts_summary: Summary of canvas diagrams and calculation artifacts.
        turn_count: Number of dialogue turns completed in the current stage.

    Returns:
        Fully compiled user prompt for stage readiness evaluation.
    """
    satisfied_str = (
        "\n".join(f"- {c}" for c in satisfied_criteria)
        if satisfied_criteria
        else "[No criteria marked satisfied yet]"
    )

    return f"""{STAGE_READINESS_SYSTEM_PROMPT}

================================================================================
STAGE READINESS EVALUATION CONTEXT
================================================================================
Current Stage: {current_stage.upper()} (Turns Completed: {turn_count})
Proposed Destination Stage: {next_stage.upper()}

Currently Satisfied Criteria:
{satisfied_str}

Architecture Artifacts & Calculations:
{artifacts_summary if artifacts_summary.strip() else "[No artifacts submitted in current stage]"}

Stage Dialogue History:
{dialogue_history if dialogue_history.strip() else "[No dialogue recorded]"}

Determine if the interview is ready to advance from {current_stage.upper()} to {next_stage.upper()}:"""

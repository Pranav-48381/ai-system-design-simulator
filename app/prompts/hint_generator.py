"""System Design Interview Simulator - Progressive Hint Generation Prompt Templates.

Implements system prompt templates, few-shot examples, and escalation directives
for the progressive 3-tier hint ladder. Empowers candidates to unblock themselves
without premature solution disclosure, strictly calibrated to target seniority levels.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import PromptContext, format_artifact_context, format_dialogue_history

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# 3-Tier Progressive Hint Ladder Specification
# -----------------------------------------------------------------------------

HINT_LADDER_SPECIFICATION = """THE 3-TIER PROGRESSIVE HINT LADDER:

TIER 1: CONCEPTUAL NUDGE (Socratic Ingestion)
- Goal: Gently redirect candidate focus toward an overlooked architectural dimension or trade-off.
- Technique: Pose a targeted reflective question. NEVER name specific technologies or direct answers.
- Example: "Think about the access patterns: is this workload read-heavy or write-heavy, and how might that influence whether we push or pull updates?"

TIER 2: SCOPED BOUNDARY (Constraint & Dimension Framing)
- Goal: Explicitly define the technical bottleneck, performance boundary, or physical constraint.
- Technique: Highlight the quantitative or systemic limitation causing the blocker.
- Example: "Notice that a single relational database instance typically bottlenecks at 10,000 write QPS, whereas our target is 50,000 write QPS. How could we distribute the write workload across multiple nodes?"

TIER 3: ARCHITECTURAL OPTIONS (Structural Trade-Off Comparison)
- Goal: Provide 2 or 3 viable design patterns or structural approaches for candidate comparison.
- Technique: Offer candidate concrete options, but require THEM to analyze pros/cons and make the final choice.
- Example: "You could consider range-based partitioning versus consistent hashing with virtual nodes. What trade-offs do you see between query flexibility and hot-spot prevention for our access pattern?"
"""

# -----------------------------------------------------------------------------
# Hint Generator System Prompt Foundation
# -----------------------------------------------------------------------------

HINT_GENERATOR_SYSTEM_PROMPT = f"""You are a master Technical Interview Mentor and System Design Architect.
A candidate is currently blocked or has explicitly requested guidance/hint on a technical challenge.
Your role is to formulate a calibrated, progressive hint following the 3-Tier Hint Ladder.

{HINT_LADDER_SPECIFICATION}

CORE GUARDRAILS:
1. NEVER GIVE AWAY THE ANSWER:
   - Even at Tier 3, present trade-offs and options rather than saying "You should use Redis here".
   - The candidate must perform the architectural reasoning and make the decision.

2. SENIORITY CALIBRATION:
   - Junior (L3): Provide encouraging scaffolding. Ensure fundamental terminology is clear.
   - Mid-Level (L4): Focus on standard architectural patterns and trade-offs (caching, relational vs NoSQL, indexes).
   - Senior (L5): Keep Tier 1 & 2 subtle. Emphasize distributed failure modes, partition schemes, and data consistency.
   - Staff / Principal (L6+): Hints should be high-level framing around blast radiuses, CAP/PACELC trade-offs, consensus limits, or cost economics.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding conversational prose or markdown formatting outside the JSON code block.
Schema:
{{
  "tier": <integer: 1, 2, or 3>,
  "hint_text": "<the spoken conversational hint delivered to the candidate in 1-3 sentences>",
  "pedagogical_intent": "<concise explanation of why this hint helps unblock without revealing the answer>",
  "suggested_follow_up": "<a probing question to help candidate continue driving the design>",
  "escalation_available": <boolean: true if tier < 3, else false>
}}
"""

# -----------------------------------------------------------------------------
# Few-Shot Reference Examples
# -----------------------------------------------------------------------------

HINT_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "topic": "Distributed ID Generation",
        "tier": 1,
        "seniority": "senior",
        "output": {
            "tier": 1,
            "hint_text": "Consider whether IDs need to be roughly time-sortable and what happens if a central sequence generator becomes unavailable.",
            "pedagogical_intent": "Prompts candidate to consider distributed sorting and single points of failure without mentioning Snowflake.",
            "suggested_follow_up": "How does time-ordering benefit our database indexing on the read path?",
            "escalation_available": True,
        },
    },
    {
        "topic": "Database Sharding Key Selection",
        "tier": 2,
        "seniority": "mid",
        "output": {
            "tier": 2,
            "hint_text": "If we partition purely by user_id, consider what happens when a celebrity user with 10 million followers posts an update versus an average user.",
            "pedagogical_intent": "Frames the specific hot-spot celebrity bottleneck constraint.",
            "suggested_follow_up": "How might we isolate or distribute high-frequency traffic across shards?",
            "escalation_available": True,
        },
    },
    {
        "topic": "Cache Invalidation & Stampedes",
        "tier": 3,
        "seniority": "staff",
        "output": {
            "tier": 3,
            "hint_text": "When a hot key expires in cache under 50k QPS, we can either use distributed mutexes with single-flight request coalescing, or pre-populate via probabilistic early expiration (XFetch). How would you evaluate the operational complexity of both?",
            "pedagogical_intent": "Presents concrete industry options while demanding deep trade-off evaluation.",
            "suggested_follow_up": "Which approach offers better resilience if our cache cluster experiences a rolling restart?",
            "escalation_available": False,
        },
    },
]

# -----------------------------------------------------------------------------
# Helpers & Prompt Builders
# -----------------------------------------------------------------------------

def format_hint_history(previous_hints: list[dict[str, Any]] | None) -> str:
    """Format previous hints delivered in the session to support progressive escalation."""
    if not previous_hints:
        return "[No prior hints delivered for this topic]"

    lines: list[str] = ["Previously Delivered Hints:"]
    for idx, hint in enumerate(previous_hints, 1):
        tier = hint.get("tier", idx)
        text = hint.get("hint_text", "")
        topic = hint.get("topic", "General")
        lines.append(f"- Hint {idx} (Tier {tier} - Topic: {topic}): \"{text}\"")
    return "\n".join(lines)


def get_hint_prompt(
    context: PromptContext,
    hint_tier: int = 1,
    topic: str = "",
    persona_prompt: str = "",
) -> str:
    """Compose the hint generation prompt for a specific tier and topic.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        hint_tier: Target hint tier level (1: Conceptual, 2: Boundary, 3: Options).
        topic: The specific technical topic or blocker (e.g. 'caching', 'sharding').
        persona_prompt: Optional interviewer persona behavioral guidance.

    Returns:
        Fully compiled user prompt string for hint generation.
    """
    hint_tier = max(1, min(3, hint_tier))
    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=15)
    artifacts_str = format_artifact_context(context.artifacts)
    examples_str = json.dumps(HINT_FEW_SHOT_EXAMPLES, indent=2)

    persona_section = (
        f"\nINTERVIEWER PERSONA GUIDANCE:\n{persona_prompt}\n"
        if persona_prompt.strip()
        else ""
    )

    return f"""{HINT_GENERATOR_SYSTEM_PROMPT}

FEW-SHOT EXAMPLES:
{examples_str}
{persona_section}
================================================================================
HINT REQUEST CONTEXT
================================================================================
Problem Title: {context.problem_title}
Active Stage: {context.current_stage.upper()}
Target Seniority Level: {context.candidate_level.upper()}
Requested Hint Tier: Tier {hint_tier} ({['Conceptual Nudge', 'Scoped Boundary', 'Architectural Options'][hint_tier - 1]})
Target Topic / Blocker: {topic if topic.strip() else "[General Stage Progression Blocker]"}

WHITEBOARD ARTIFACTS & CALCULATIONS:
{artifacts_str}

RECENT DIALOGUE TRANSCRIPT:
{dialogue_str}

Formulate a Tier {hint_tier} hint according to the JSON schema:"""


def get_progressive_hint_prompt(
    context: PromptContext,
    previous_hints: list[dict[str, Any]] | None = None,
    topic: str = "",
    persona_prompt: str = "",
) -> str:
    """Compose progressive hint prompt automatically escalating tier based on prior hint history.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        previous_hints: List of hint dictionaries previously generated for this session.
        topic: The specific technical topic or blocker.
        persona_prompt: Optional interviewer persona instructions.

    Returns:
        Fully compiled user prompt string for progressive hint generation.
    """
    count = len(previous_hints) if previous_hints else 0
    next_tier = min(3, count + 1)
    history_str = format_hint_history(previous_hints)

    prompt = get_hint_prompt(
        context=context,
        hint_tier=next_tier,
        topic=topic,
        persona_prompt=persona_prompt,
    )

    return f"""{prompt}

================================================================================
PRIOR HINT ESCALATION HISTORY
================================================================================
{history_str}
Escalation Status: Providing Tier {next_tier} hint building upon prior guidance.
"""

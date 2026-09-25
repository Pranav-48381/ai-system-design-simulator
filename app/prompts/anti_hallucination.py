"""System Design Interview Simulator - Anti-Hallucination & Grounding Prompt Templates.

Implements prompt guards, fact-checking verifiers, and physical invariant anchors to prevent
LLM hallucinations, false candidate attribution, timeline amnesia, and unrealistic physics claims
during multi-turn autonomous system design interviews.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.prompts.base import PromptContext, format_artifact_context, format_dialogue_history

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Physical Distributed Systems Invariants (Numbers Every Engineer Should Know)
# -----------------------------------------------------------------------------

PHYSICAL_SYSTEMS_INVARIANTS: dict[str, str] = {
    "l1_cache_ref": "L1 cache reference: ~0.5-1 ns",
    "ram_access": "Main memory (RAM) reference: ~100 ns",
    "ssd_random_read": "Solid-state drive (NVMe SSD) random read: ~10-100 µs",
    "hdd_seek": "Rotational hard disk seek: ~5-10 ms",
    "intradc_rtt": "Same datacenter network round trip: ~0.5 ms",
    "transatlantic_rtt": "Transatlantic round trip (e.g., NY to London): ~60-80 ms",
    "transpacific_rtt": "Transpacific round trip (e.g., SF to Tokyo): ~120-150 ms",
    "rdbms_single_node_write_qps": "Single-node unpartitioned RDBMS write ceiling: ~5,000 - 15,000 QPS",
    "redis_single_node_qps": "Single-threaded Redis in-memory operation ceiling: ~100,000 - 150,000 QPS",
    "network_10gbps_nic": "Standard 10 Gbps network card wire throughput limit: ~1.25 GB/s (10 Gbit/8)",
}

# -----------------------------------------------------------------------------
# Anti-Hallucination & Grounding Guard System Prompt
# -----------------------------------------------------------------------------

ANTI_HALLUCINATION_SYSTEM_PROMPT = """You are an objective AI Interviewer Fact-Checker and Grounding Guard.
Your mission is to audit a proposed interviewer response before it is delivered to the candidate,
verifying that the interviewer's critique, challenge, or statements are strictly factual, grounded,
and consistent with the established conversation history.

FOUR CRITICAL AUDIT DIMENSIONS:
1. FALSE ATTRIBUTION CHECK:
   - Does the proposed response claim the candidate said, proposed, or decided something they never actually said?
   - Example Violation: "Earlier you chose MySQL" when the transcript shows the candidate chose DynamoDB.

2. PROBLEM CONSTRAINT FIDELITY:
   - Does the proposed response invent arbitrary problem constraints or change the problem specification?
   - Example Violation: Suddenly requiring the candidate to support video encoding when the problem is a URL Shortener.

3. ESTABLISHED STATE CONSISTENCY:
   - Does the interviewer ask about a decision that was already settled in an earlier stage, ignoring previous turns?
   - Example Violation: Asking "What is your target QPS?" in Stage 4 when QPS was already thoroughly estimated in Stage 2.

4. PHYSICAL & ARCHITECTURAL REALISM:
   - Does the response endorse or make claims that violate fundamental physical distributed systems laws?
   - Violations include claiming sub-millisecond global roundtrips across continents, or infinite single-node SSD throughput.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding conversational prose or markdown formatting outside the JSON code block.
Schema:
{
  "is_grounded": <boolean: true if response passes all 4 dimensions, false if any hallucination detected>,
  "confidence_score": <float between 0.0 and 1.0>,
  "detected_violations": [
    {
      "dimension": "<false_attribution | constraint_fidelity | state_consistency | physical_realism>",
      "issue_description": "<concise explanation of what is ungrounded or contradicted>",
      "offending_text_snippet": "<exact phrase in proposed response>"
    }
  ],
  "factual_anchors_verified": ["<anchor 1>", "<anchor 2>"],
  "sanitized_response": "<the original response if grounded, or a corrected grounded version with hallucinations removed>"
}
"""

# -----------------------------------------------------------------------------
# Few-Shot Reference Examples
# -----------------------------------------------------------------------------

ANTI_HALLUCINATION_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "context": {
            "problem": "Design a Distributed Rate Limiter",
            "candidate_stated": "I will use Redis with a Sliding Window Counter algorithm.",
        },
        "proposed_response": "Since you decided to use PostgreSQL for rate-limit counting, how will you prevent database lock contention under 100k QPS?",
        "output": {
            "is_grounded": False,
            "confidence_score": 0.99,
            "detected_violations": [
                {
                    "dimension": "false_attribution",
                    "issue_description": "Interviewer claims candidate chose PostgreSQL when candidate actually chose Redis Sliding Window.",
                    "offending_text_snippet": "Since you decided to use PostgreSQL for rate-limit counting",
                }
            ],
            "factual_anchors_verified": ["Candidate stated: Redis with Sliding Window Counter"],
            "sanitized_response": "Since you decided to use Redis for rate-limit counting, how will you prevent race conditions and lock contention under 100k QPS?",
        },
    },
    {
        "context": {
            "problem": "Global Video Streaming Platform",
            "candidate_stated": "We will replicate metadata across US-East and EU-West with synchronous 2-phase commit to ensure zero latency impact.",
        },
        "proposed_response": "That sounds great, since US-East to EU-West synchronous roundtrips only take 2 milliseconds, that won't add any user-perceived lag.",
        "output": {
            "is_grounded": False,
            "confidence_score": 0.98,
            "detected_violations": [
                {
                    "dimension": "physical_realism",
                    "issue_description": "Interviewer asserts transatlantic RTT is only 2ms, violating speed-of-light in fiber (actual RTT is 70-80ms).",
                    "offending_text_snippet": "since US-East to EU-West synchronous roundtrips only take 2 milliseconds",
                }
            ],
            "factual_anchors_verified": ["Transatlantic RTT physical invariant: ~60-80 ms minimum"],
            "sanitized_response": "Keep in mind that transatlantic roundtrips between US-East and EU-West take at least 70-80 ms. How will a synchronous 2-phase commit affect user-perceived latency on writes?",
        },
    },
]

# -----------------------------------------------------------------------------
# Helpers & Prompt Builders
# -----------------------------------------------------------------------------

def format_grounding_anchors(context: PromptContext) -> str:
    """Format ground-truth problem constraints, established decisions, and physical invariants."""
    lines: list[str] = [
        f"Problem Specification: {context.problem_title}",
        f"Description: {context.problem_description}",
        f"Scale Targets: {json.dumps(context.scale_targets)}",
        f"Active Stage: {context.current_stage.upper()}",
        f"Satisfied Criteria So Far: {', '.join(context.satisfied_criteria) if context.satisfied_criteria else 'None'}",
        "\nCore Distributed Systems Physical Invariants:",
    ]
    for key, desc in PHYSICAL_SYSTEMS_INVARIANTS.items():
        lines.append(f"- {desc}")

    return "\n".join(lines)


def get_anti_hallucination_guard_prompt(
    proposed_response: str,
    context: PromptContext,
) -> str:
    """Compose prompt to audit a proposed interviewer response for hallucinations and consistency.

    Args:
        proposed_response: Candidate response drafted by interviewer agent.
        context: Ground truth session state, problem details, and dialogue history.

    Returns:
        Fully compiled user prompt string for anti-hallucination verification.
    """
    anchors_str = format_grounding_anchors(context)
    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=20)
    artifacts_str = format_artifact_context(context.artifacts)
    examples_str = json.dumps(ANTI_HALLUCINATION_FEW_SHOT_EXAMPLES, indent=2)

    return f"""{ANTI_HALLUCINATION_SYSTEM_PROMPT}

FEW-SHOT AUDIT EXAMPLES:
{examples_str}

================================================================================
GROUND TRUTH ANCHORS & CONSTRAINTS
================================================================================
{anchors_str}

WHITEBOARD ARTIFACTS:
{artifacts_str}

RECENT DIALOGUE TRANSCRIPT (CANONICAL HISTORY):
{dialogue_str}

================================================================================
PROPOSED INTERVIEWER RESPONSE TO AUDIT
================================================================================
\"\"\"
{proposed_response.strip()}
\"\"\"

Audit the proposed response and output the verification JSON object:"""


def get_grounding_verification_prompt(
    claim: str,
    reference_facts: dict[str, Any] | list[str],
) -> str:
    """Compose a targeted verification prompt checking whether a single factual claim is supported by reference facts.

    Args:
        claim: The specific technical assertion to verify.
        reference_facts: Ground-truth reference facts or transcript lines.

    Returns:
        Prompt string requesting boolean verification and reasoning.
    """
    facts_str = (
        json.dumps(reference_facts, indent=2)
        if isinstance(reference_facts, dict)
        else "\n".join(f"- {f}" for f in reference_facts)
    )

    return f"""You are a precise technical verifier.
Determine whether the following CLAIM is completely supported by and consistent with the REFERENCE FACTS.

CLAIM:
\"{claim.strip()}\"

REFERENCE FACTS:
{facts_str}

STRICT JSON OUTPUT:
{{
  "is_supported": <boolean>,
  "confidence": <float between 0.0 and 1.0>,
  "discrepancies": ["<list of contradictions if any>"],
  "reasoning": "<concise explanation>"
}}"""

"""System Design Interview Simulator - Clarification Stage Prompt Templates.

Implements system prompt templates, probing strategies, criteria checklists,
and conversational guidelines for the Requirements & Clarification interview stage.
Guides candidates to uncover functional scope, non-functional SLOs/SLAs, and boundaries.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import BasePromptBuilder, PromptContext, render_base_system_prompt

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Clarification Stage Core Meta-Instructions
# -----------------------------------------------------------------------------

CLARIFICATION_STAGE_DIRECTIVE = """STAGE GOAL: REQUIREMENTS DISCOVERY & SCOPE CLARIFICATION
You are conducting the initial phase of the system design interview. Your goal is to assess
the candidate's ability to clarify ambiguous problem statements, scope core functional features,
quantify non-functional expectations (SLAs/SLOs), and define crisp system boundaries.

CRITICAL BEHAVIORAL DIRECTIVES:
1. DO NOT VOLUNTEER THE REQUIREMENTS:
   - When the problem is introduced, allow the candidate to lead the discovery.
   - If the candidate asks open-ended clarification questions (e.g. "Should we support analytics?"),
     answer realistically based on the ground truth problem specification.
   - If the candidate makes arbitrary assumptions without checking, challenge them gently:
     "What makes you assume read traffic will dominate writes 100:1 in this specific use case?"

2. ENFORCE BOUNDARY SCOPING:
   - Ensure the candidate explicitly states what is IN-SCOPE and what is OUT-OF-SCOPE.
   - Acknowledge good scoping choices: "Focusing on core 1:1 messaging first before group chats is a solid approach."

3. CALIBRATE TO CANDIDATE SENIORITY:
   - Mid-Level (L4): Guide them if they focus solely on happy-path functional requirements and forget latency or availability.
   - Senior (L5): Expect them to drive the taxonomy (P99 latency, availability 9s, consistency vs availability).
   - Staff (L6+): Expect immediate discussions of business blast radius, data sovereignty/compliance, multi-tenancy, and operational SLAs.

4. TRANSITION READINESS:
   - Once 2-4 core functional requirements, key non-functional targets (availability, latency), and scope boundaries
     are established, prompt the candidate to transition to Capacity Estimation:
     "These requirements look solid and well-scoped. Let's move on to estimating scale and capacity."
"""

# Probing questions library categorized by clarification area
CLARIFICATION_PROBES: dict[str, list[str]] = {
    "functional": [
        "What are the top 2 or 3 user actions that the system must handle flawlessly?",
        "Are there administrative or reporting workflows we need to support in MVP, or can we defer those?",
        "How should the system handle updates or deletions of existing records?",
    ],
    "non_functional": [
        "What are our latency expectations for the read path versus the write path (e.g. P99 < 100ms)?",
        "How critical is high availability versus strong consistency for this data domain (CAP/PACELC)?",
        "What are the availability targets (e.g. 99.9% vs 99.99%) and what is the cost of downtime?",
        "Is this a globally distributed user base or centralized within a single geographical region?",
    ],
    "scale_and_constraints": [
        "What is our projected scale in terms of Daily Active Users (DAU) and total user base?",
        "What is the expected read-to-write ratio?",
        "Are there regulatory or compliance constraints (e.g., GDPR, HIPAA, data retention)?",
    ],
}


def format_missing_clarification_criteria(satisfied_criteria: list[str]) -> list[str]:
    """Identify which essential clarification criteria remain unaddressed."""
    essential = [
        ("functional_scope", "Define 2-3 core functional requirements and out-of-scope boundaries."),
        ("scale_metrics", "Clarify traffic scale (DAU/MAU) and read vs write ratio."),
        ("latency_slo", "Specify latency targets (e.g. P95/P99 latency SLA)."),
        ("availability_slo", "Clarify availability target (e.g. 99.9% vs 99.99%) and consistency model."),
    ]
    satisfied_set = {c.lower() for c in satisfied_criteria}
    missing: list[str] = []
    for key, desc in essential:
        if not any(key in s for s in satisfied_set):
            missing.append(desc)
    return missing


def get_clarification_prompt(
    context: PromptContext,
    persona_prompt: str = "",
    missing_criteria: list[str] | None = None,
) -> str:
    """Build the complete system prompt for the Clarification & Requirements stage.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.
        missing_criteria: Optional explicitly provided list of unfulfilled criteria.

    Returns:
        Fully compiled system prompt string ready for LLM invocation.
    """
    builder = BasePromptBuilder(context).with_persona(persona_prompt)
    builder.with_stage_instruction(CLARIFICATION_STAGE_DIRECTIVE)

    # Check for missing stage criteria to give actionable steering
    criteria_to_check = (
        missing_criteria
        if missing_criteria is not None
        else format_missing_clarification_criteria(context.satisfied_criteria)
    )

    if criteria_to_check:
        guards = [
            f"Unaddressed Stage Goal: {criterion}"
            for criterion in criteria_to_check
        ]
        builder.with_guard_instructions(guards)

    # Add seniority-calibrated guidelines
    lvl = context.candidate_level.lower()
    if lvl == SeniorityLevel.MID.value:
        builder.with_section(
            "Clarification Stage Coaching (Mid-Level)",
            "The candidate may miss latency or availability numbers. If they define features without SLAs, "
            "ask: 'What kind of latency and availability targets should we design for?'",
        )
    elif lvl == SeniorityLevel.STAFF.value:
        builder.with_section(
            "Clarification Stage Rigor (Staff-Level)",
            "Expect the candidate to define multi-region boundaries, compliance/data residency, and failure "
            "tolerances without prompting. If they omit these, ask how compliance and cross-region latencies "
            "affect the architecture.",
        )

    return builder.build_system_prompt()

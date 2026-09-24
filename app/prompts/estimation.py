"""System Design Interview Simulator - Capacity Estimation Stage Prompt Templates.

Implements system prompt templates, arithmetic validation directives, unit conversion
helpers, and conversational guidance for the Back-of-the-Envelope Capacity Estimation stage.
Guides candidates through QPS, storage growth, network bandwidth, and cache memory sizing.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import BasePromptBuilder, PromptContext

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Capacity Estimation Core Meta-Instructions
# -----------------------------------------------------------------------------

ESTIMATION_STAGE_DIRECTIVE = """STAGE GOAL: BACK-OF-THE-ENVELOPE CAPACITY ESTIMATION
You are guiding the candidate through quantitative capacity estimation. The objective is not
to test rote arithmetic tricks, but to assess whether the candidate can estimate system scale
and translate those quantitative bounds into actionable architectural design decisions.

KEY QUANTITATIVE DIMENSIONS TO COVER:
1. TRAFFIC THROUGHPUT (QPS):
   - Daily Active Users (DAU) and read/write requests per user.
   - Average Read QPS and Write QPS calculation.
   - Peak QPS multiplier (typically 2x to 5x average for spikes).

2. STORAGE VOLUME & CAPACITY GROWTH:
   - Average size per data record / metadata payload.
   - Daily write volume and 5-year or 10-year cumulative storage requirement.
   - Replication factor (e.g., 3x replication factor) plus 20-30% operational headroom.

3. NETWORK BANDWIDTH & THROUGHPUT:
   - Ingress throughput (Write QPS * Write payload size in MB/s or Gbps).
   - Egress throughput (Read QPS * Read payload size in MB/s or Gbps).

4. MEMORY & CACHE CAPACITY (80/20 RULE):
   - Estimating hot working set: Caching top 20% of daily read requests.
   - Total RAM required for Redis / Memcached cluster.

CRITICAL INTERVIEWER BEHAVIORAL DIRECTIVES:
1. APPROXIMATIONS ARE ENCOURAGED:
   - Praise smart rounding that simplifies mental arithmetic (e.g., 86,400 seconds/day ≈ 100,000 seconds).
   - Do NOT get bogged down in microscopic decimal disputes if the candidate's magnitude is correct.

2. CONNECT NUMBERS TO ARCHITECTURE:
   - Always push the candidate to explain what the number means for the design:
     "At 25,000 write QPS, can a single primary database handle this, or do we need partitioning?"
     "At 5 TB of storage per day, how does this affect our backup and indexing strategy?"

3. PROGRESSIVE HINTING:
   - If the candidate struggles with formulas:
     Step 1: Remind them of the formula conceptually ("How many seconds are in a day, and how many daily requests does that yield per second?").
     Step 2: Provide the base metric ("Assume 100 million DAU, each writing 2 records per day").
     Step 3: Assist with the ballpark division.

4. TRANSITION READINESS:
   - Once Read/Write QPS, long-term storage, and cache memory estimates are defined and
     connected to architectural scale, prompt transition to High-Level Architecture:
     "The capacity estimates give us clear scale targets. Let's translate these numbers into our High-Level Architecture."
"""

# Mental math rule-of-thumb approximations for quick grounding
ESTIMATION_REFERENCE_RULES: dict[str, str] = {
    "seconds_per_day": "86,400 seconds ≈ 100,000 seconds (10^5) for back-of-the-envelope calculations",
    "qps_shortcut": "1 million requests/day ≈ 12 QPS (or ~10 QPS using 100k s/day simplification)",
    "storage_units": "1 KB = 10^3 bytes, 1 MB = 10^6 bytes, 1 GB = 10^9 bytes, 1 TB = 10^12 bytes, 1 PB = 10^15 bytes",
    "cache_rule": "80/20 Pareto principle: 20% of hot keys generate 80% of traffic; cache the 20% daily working set in RAM",
}

# Targeted probing questions for estimation verification
ESTIMATION_PROBES: dict[str, list[str]] = {
    "qps": [
        "What peak traffic multiplier are you assuming for traffic bursts or marketing events?",
        "How did you break down the ratio between read operations and write operations?",
    ],
    "storage": [
        "Have you factored in database indexes, metadata overhead, and 3x replica storage amplification?",
        "What is the expected data retention window (e.g. 5 years vs indefinitely)?",
    ],
    "bandwidth": [
        "What is our projected network egress bandwidth? Will this saturate standard 10 Gbps network cards?",
        "Does media content (images, videos) get served from our backend or offloaded to a CDN edge?",
    ],
    "cache": [
        "Applying the 80/20 rule, how much RAM would our caching cluster need to hold 20% of daily read volume?",
        "If a cache node restarts, what is the recovery time and cache hit ratio warm-up penalty?",
    ],
}


def format_missing_estimation_criteria(satisfied_criteria: list[str]) -> list[str]:
    """Identify which essential estimation criteria remain unaddressed."""
    essential = [
        ("qps_throughput", "Estimate Read QPS, Write QPS, and Peak traffic multiplier."),
        ("storage_growth", "Calculate daily data ingress and multi-year cumulative storage capacity."),
        ("bandwidth", "Calculate network ingress and egress throughput (MB/s or Gbps)."),
        ("cache_sizing", "Size cache RAM requirements using the 80/20 Pareto distribution rule."),
    ]
    satisfied_set = {c.lower() for c in satisfied_criteria}
    missing: list[str] = []
    for key, desc in essential:
        if not any(key in s for s in satisfied_set):
            missing.append(desc)
    return missing


def get_estimation_prompt(
    context: PromptContext,
    persona_prompt: str = "",
    missing_criteria: list[str] | None = None,
) -> str:
    """Build the complete system prompt for the Capacity Estimation stage.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.
        missing_criteria: Optional explicitly provided list of unfulfilled criteria.

    Returns:
        Fully compiled system prompt string ready for LLM invocation.
    """
    builder = BasePromptBuilder(context).with_persona(persona_prompt)
    builder.with_stage_instruction(ESTIMATION_STAGE_DIRECTIVE)

    # Reference rules for grounding calculations
    rules_text = "\n".join(f"- {k}: {v}" for k, v in ESTIMATION_REFERENCE_RULES.items())
    builder.with_section("Estimation Mental Math Reference Guide", rules_text)

    # Criteria tracking
    criteria_to_check = (
        missing_criteria
        if missing_criteria is not None
        else format_missing_estimation_criteria(context.satisfied_criteria)
    )

    if criteria_to_check:
        guards = [
            f"Unaddressed Estimation Target: {criterion}"
            for criterion in criteria_to_check
        ]
        builder.with_guard_instructions(guards)

    # Seniority calibration
    lvl = context.candidate_level.lower()
    if lvl == SeniorityLevel.MID.value:
        builder.with_section(
            "Capacity Estimation Coaching (Mid-Level)",
            "Be patient with mental arithmetic. If the candidate struggles, encourage them to round "
            "86,400 seconds to 100,000 seconds. Help them verify that MB vs GB conversions are correct.",
        )
    elif lvl == SeniorityLevel.STAFF.value:
        builder.with_section(
            "Capacity Estimation Rigor (Staff-Level)",
            "Do not accept raw numbers in isolation. Demand hardware implications: disk IOPS limits, "
            "network interface card (NIC) saturation, cold storage tiering costs, and memory footprint "
            "per cache instance.",
        )

    return builder.build_system_prompt()

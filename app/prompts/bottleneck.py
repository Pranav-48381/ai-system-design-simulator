"""System Design Interview Simulator - Bottlenecks & Resilience Stage Prompt Templates.

Implements system prompt templates, failure mode scenarios, single point of failure (SPOF)
identification directives, and resilience analysis for the Bottlenecks & Trade-offs stage.
Guides candidates through circuit breakers, rate limiting, cascading failure prevention, and failover.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import BasePromptBuilder, PromptContext

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Bottlenecks & Trade-offs Core Meta-Instructions
# -----------------------------------------------------------------------------

BOTTLENECK_STAGE_DIRECTIVE = """STAGE GOAL: BOTTLENECKS, FAILURE MODES & RESILIENCE ANALYSIS
You are evaluating the system's robustness, fault tolerance, and trade-offs. No system design
is complete without stress-testing its breaking points, identifying single points of failure (SPOFs),
and designing graceful degradation strategies under adverse conditions.

KEY RESILIENCE DIMENSIONS TO PROBE:
1. SINGLE POINTS OF FAILURE (SPOFs):
   - Identifying single master databases, un-clustered caches, non-redundant load balancers, or single AZ dependencies.
   - Multi-AZ deployment and automated failover topologies (e.g. warm standby with heartbeat monitoring).

2. CASCADING FAILURES & LATENCY SPIKES:
   - What happens when a downstream service slows down or becomes unreachable?
   - Preventing retry storms and thread pool exhaustion using:
     * Circuit Breakers (Closed -> Open -> Half-Open state machine).
     * Bulkhead isolation (isolated worker thread pools and connection limits).
     * Exponential backoff with randomized jitter.

3. LOAD SHEDDING & TRAFFIC REGULATION:
   - Rate limiting algorithms: Token Bucket, Leaky Bucket, Sliding Window Log/Counter.
   - Rate limiter placement: Edge CDN vs API Gateway vs Service Mesh.
   - Handling HTTP 429 Too Many Requests with Retry-After headers.
   - Graceful degradation: Shedding non-critical background jobs or features during extreme traffic surges.

4. DATA RESILIENCE & DISASTER RECOVERY:
   - RPO (Recovery Point Objective - maximum acceptable data loss window).
   - RTO (Recovery Time Objective - maximum acceptable downtime duration).
   - Backup strategies, cross-region replication lag, and split-brain resolution during network partitions.

CRITICAL INTERVIEWER BEHAVIORAL DIRECTIVES:
1. INTRODUCE CONCRETE CHAOS SCENARIOS:
   - Challenge the candidate with realistic production incidents:
     "Your primary database instance experiences a hard kernel panic right now. Walk me through the exact failover sequence."
     "A promotional campaign causes traffic to surge by 10x within 30 seconds. Where does the system fail first?"

2. DEMAND EXPLICIT TRADE-OFF ARTICULATION:
   - Every architectural choice has a downside. Ask the candidate to articulate what they sacrificed:
     "You chose strong consistency here. What is the impact on write latency and availability during a cross-region network partition (PACELC)?"

3. DO NOT ACCEPT TRIVIAL 'JUST ADD MORE SERVERS' ANSWERS:
   - If the candidate says "Horizontal auto-scaling handles it", probe the limits:
     "Auto-scaling takes 3 to 5 minutes to spin up new VM/container instances. How does the system survive the immediate spike without crashing?"

4. TRANSITION READINESS:
   - Once SPOFs, failure modes, rate limiting, and trade-offs are thoroughly explored,
     prompt transition to the final Evaluation & Debrief stage:
     "We have thoroughly stress-tested the resilience and trade-offs of your architecture. Let's move to our final Evaluation & Debrief stage."
"""

# Concrete chaos scenarios to challenge candidates with
BOTTLENECK_CHAOS_SCENARIOS: dict[str, str] = {
    "database_master_crash": (
        "The primary database node crashes unexpectedly. How is the standby promoted, "
        "how do application servers update their write connection pool, and is any in-flight write data lost?"
    ),
    "cache_cluster_outage": (
        "A network switch failure makes the entire Redis cluster unreachable for 60 seconds. "
        "How do you prevent the thundering herd from instantly crashing the underlying relational database?"
    ),
    "downstream_dependency_hang": (
        "An external payment or notification partner API begins taking 15 seconds per call instead of 200ms. "
        "How do you stop your upstream web servers from exhausting their thread pools and dropping incoming user traffic?"
    ),
    "traffic_spike_10x": (
        "A breaking news event or viral post causes a sudden 10x traffic spike in 15 seconds. "
        "How does your ingress tier shed load or rate limit to protect core platform availability?"
    ),
}

# Probing questions categorized by resilience dimension
BOTTLENECK_PROBES: dict[str, list[str]] = {
    "spof": [
        "Looking at your architecture canvas, what is the single biggest single point of failure right now?",
        "If Availability Zone 1 goes completely dark, what happens to ongoing transactions and user sessions?",
    ],
    "cascading_failure": [
        "Where are your circuit breakers configured, and what error threshold or timeout triggers them to trip open?",
        "How do you prevent client retry storms from amplifying load against an already struggling service?",
    ],
    "rate_limiting": [
        "Which rate limiting algorithm would you implement (Token Bucket vs Sliding Window), and why?",
        "Where should rate limiting live: at the edge API gateway or inside individual application services?",
    ],
    "trade_offs": [
        "What did you sacrifice in this design to achieve low latency? Consistency, operational complexity, or cost?",
        "If business leadership mandates a 50% infrastructure cost reduction, what components would you re-architect first?",
    ],
}


def format_missing_bottleneck_criteria(satisfied_criteria: list[str]) -> list[str]:
    """Identify which essential bottleneck criteria remain unaddressed."""
    essential = [
        ("spof_identification", "Identify Single Points of Failure (SPOFs) and propose redundancy/failover."),
        ("failure_modes", "Address downstream failures via circuit breakers, timeouts, or bulkhead isolation."),
        ("rate_limiting", "Design rate limiting / load shedding to handle traffic surges and protect backends."),
        ("trade_off_analysis", "Articulate key trade-offs (CAP/PACELC, cost vs latency, consistency vs availability)."),
    ]
    satisfied_set = {c.lower() for c in satisfied_criteria}
    missing: list[str] = []
    for key, desc in essential:
        if not any(key in s for s in satisfied_set):
            missing.append(desc)
    return missing


def get_bottleneck_prompt(
    context: PromptContext,
    persona_prompt: str = "",
    missing_criteria: list[str] | None = None,
) -> str:
    """Build the complete system prompt for the Bottlenecks & Resilience stage.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.
        missing_criteria: Optional explicitly provided list of unfulfilled criteria.

    Returns:
        Fully compiled system prompt string ready for LLM invocation.
    """
    builder = BasePromptBuilder(context).with_persona(persona_prompt)
    builder.with_stage_instruction(BOTTLENECK_STAGE_DIRECTIVE)

    # Criteria tracking
    criteria_to_check = (
        missing_criteria
        if missing_criteria is not None
        else format_missing_bottleneck_criteria(context.satisfied_criteria)
    )

    if criteria_to_check:
        guards = [
            f"Unaddressed Resilience Goal: {criterion}"
            for criterion in criteria_to_check
        ]
        builder.with_guard_instructions(guards)

    # Seniority calibration
    lvl = context.candidate_level.lower()
    if lvl == SeniorityLevel.MID.value:
        builder.with_section(
            "Bottlenecks Stage Coaching (Mid-Level)",
            "Mid-level candidates often overlook circuit breakers and retry storms. Guide them: "
            "'What happens if the database is under heavy load and clients keep retrying every 100ms?' "
            "Help them recognize the value of exponential backoff and jitter.",
        )
    elif lvl == SeniorityLevel.STAFF.value:
        builder.with_section(
            "Bottlenecks Stage Rigor (Staff-Level)",
            "Staff-level candidates must master cross-datacenter failure domains: split-brain detection, "
            "Raft consensus leader re-election delays, PACELC theorem trade-offs, formal RPO/RTO error budgets, "
            "and chaos engineering injection testing.",
        )

    return builder.build_system_prompt()

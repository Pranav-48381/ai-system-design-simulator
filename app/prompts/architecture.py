"""System Design Interview Simulator - High-Level Architecture Stage Prompt Templates.

Implements system prompt templates, API design critique directives, data flow analysis,
and conversational guidance for the High-Level Architecture stage.
Guides candidates through component decomposition, API contracts, and async decoupling.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import BasePromptBuilder, PromptContext

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# High-Level Architecture Core Meta-Instructions
# -----------------------------------------------------------------------------

ARCHITECTURE_STAGE_DIRECTIVE = """STAGE GOAL: HIGH-LEVEL ARCHITECTURE & COMPONENT DECOMPOSITION
You are evaluating the candidate's macro-architectural design. The candidate must establish
an end-to-end data flow from client requests through ingress, application services,
asynchronous processing pipelines, and persistence layers.

KEY ARCHITECTURAL PILLARS TO EVALUATE:
1. CLIENT-TO-BACKEND INGRESS:
   - Client interaction (Web, Mobile, Public API).
   - DNS routing, CDN caching for static/media assets.
   - Reverse Proxy / Load Balancer (L4 vs L7) and API Gateway (rate limiting, auth, routing).

2. CORE SERVICE DECOMPOSITION:
   - Logical separation of microservices or modular service boundaries.
   - Decoupling read paths from write paths (CQRS pattern where appropriate).
   - Clear stateless application layer to enable horizontal auto-scaling.

3. ASYNCHRONOUS DECOUPLING & MESSAGE BROKERS:
   - Using message queues (e.g., Kafka, RabbitMQ, SQS) to decouple heavy processing from client request-response loops.
   - Event-driven data propagation and background worker pools.

4. API CONTRACT DESIGN:
   - Crisp REST or gRPC endpoint definitions.
   - Accurate HTTP methods, query/path parameters, request payloads, and status codes.
   - Architectural nuances (e.g., 301 Permanent Redirect vs 302 Found in URL shortening).

CRITICAL INTERVIEWER BEHAVIORAL DIRECTIVES:
1. ENCOURAGE WHITEBOARD VISUALIZATION:
   - Ask the candidate to visualize the flow or sketch components:
     "Can you trace the path of a write request from the client down to the database?"
     "How do your application servers communicate with the background workers?"

2. PROBE SYNCHRONOUS VS ASYNCHRONOUS BOUNDARIES:
   - If the candidate makes heavy inter-service calls synchronously over HTTP, challenge the latency:
     "If Service A synchronously calls Service B and Service C before responding, what happens to P99 latency when Service C slows down?"

3. CHALLENGE "MAGIC" BOXES:
   - Reject vague boxes like "Processing Engine" or "Big Data Layer". Demand clear functional responsibilities.

4. TRANSITION READINESS:
   - Once core services, API contracts, ingress flow, and data stores are identified on the architecture canvas,
     prompt transition to Deep Dive:
     "The overall architecture is clear and well-structured. Let's zoom in on a component Deep Dive—specifically the data model, storage engine, and caching strategy."
"""

# Probing questions library categorized by architectural dimension
ARCHITECTURE_PROBES: dict[str, list[str]] = {
    "api_design": [
        "What does the exact request and response payload look like for this primary endpoint?",
        "What HTTP status codes will this endpoint return for validation errors, rate limits, and service failures?",
        "How do we handle request idempotency to prevent duplicate operations on network retries?",
    ],
    "ingress_and_networking": [
        "What is the role of your API Gateway versus your Load Balancers in this topology?",
        "Where do authentication, rate limiting, and SSL/TLS termination occur in your ingress pipeline?",
    ],
    "service_boundaries": [
        "Are your application servers stateful or stateless? How do you scale them horizontally?",
        "Why did you choose synchronous REST/gRPC over an asynchronous event-driven model for this interaction?",
    ],
    "asynchronous_flow": [
        "What message broker are you proposing, and what guarantees does it provide (at-least-once vs exactly-once)?",
        "How does the client discover when a long-running asynchronous background job finishes?",
    ],
}


def format_missing_architecture_criteria(satisfied_criteria: list[str]) -> list[str]:
    """Identify which essential architecture criteria remain unaddressed."""
    essential = [
        ("api_contracts", "Define core API endpoints (methods, paths, payloads, status codes)."),
        ("service_decomposition", "Define primary microservices/modules and their responsibilities."),
        ("ingress_routing", "Specify client ingress path (DNS, CDN, API Gateway, Load Balancer)."),
        ("async_decoupling", "Identify asynchronous background workflows and message queuing."),
    ]
    satisfied_set = {c.lower() for c in satisfied_criteria}
    missing: list[str] = []
    for key, desc in essential:
        if not any(key in s for s in satisfied_set):
            missing.append(desc)
    return missing


def get_architecture_prompt(
    context: PromptContext,
    persona_prompt: str = "",
    missing_criteria: list[str] | None = None,
) -> str:
    """Build the complete system prompt for the High-Level Architecture stage.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.
        missing_criteria: Optional explicitly provided list of unfulfilled criteria.

    Returns:
        Fully compiled system prompt string ready for LLM invocation.
    """
    builder = BasePromptBuilder(context).with_persona(persona_prompt)
    builder.with_stage_instruction(ARCHITECTURE_STAGE_DIRECTIVE)

    # Criteria tracking
    criteria_to_check = (
        missing_criteria
        if missing_criteria is not None
        else format_missing_architecture_criteria(context.satisfied_criteria)
    )

    if criteria_to_check:
        guards = [
            f"Unaddressed Architecture Goal: {criterion}"
            for criterion in criteria_to_check
        ]
        builder.with_guard_instructions(guards)

    # Seniority calibration
    lvl = context.candidate_level.lower()
    if lvl == SeniorityLevel.MID.value:
        builder.with_section(
            "Architecture Stage Coaching (Mid-Level)",
            "Mid-level candidates often draw a single app server box and database. Guide them: "
            "'How would we separate our public read API from the background ingestion pipeline?' "
            "Validate basic client-server and caching tiers.",
        )
    elif lvl == SeniorityLevel.STAFF.value:
        builder.with_section(
            "Architecture Stage Rigor (Staff-Level)",
            "Expect a clear distributed systems narrative: decoupled CQRS event sourcing, zero-trust "
            "service mesh mTLS, ingress edge routing, reverse proxy connection pooling, and multi-region "
            "traffic shedding.",
        )

    return builder.build_system_prompt()

"""System Design Interview Simulator - Base Prompt Foundation.

Defines foundational meta-instructions, candidate seniority calibration matrices,
dialogue and whiteboard state formatters, and fluent prompt builders orchestrating
interviewer behavior across all system design interview stages.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel, SpeakerRole

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Seniority Level Expectation Matrices
# -----------------------------------------------------------------------------

SENIORITY_EXPECTATIONS: dict[str, str] = {
    SeniorityLevel.MID.value: (
        "Candidate Level: MID-LEVEL SOFTWARE ENGINEER (L4 / SDE II)\n"
        "- Expected to identify 2-3 primary functional requirements and basic non-functional constraints.\n"
        "- Able to calculate ballpark QPS and basic storage requirements with reasonable arithmetic accuracy.\n"
        "- Designs clear client-server architectures with logical component separation.\n"
        "- Understands basic database schemas and standard caching (e.g., Redis lookaside).\n"
        "- Interviewer Guidance: Provide occasional structure if candidate wanders. Accept standard "
        "industry patterns; do not demand deep consensus protocol or cross-region replication details."
    ),
    SeniorityLevel.SENIOR.value: (
        "Candidate Level: SENIOR SOFTWARE ENGINEER (L5 / Senior SDE)\n"
        "- Expected to independently lead the discussion, drive scope definition, and proactively suggest scale targets.\n"
        "- Accurate estimation of storage, write/read QPS, network bandwidth, and memory cache footprints.\n"
        "- Delivers end-to-end architecture with clear data flow, asynchronous queues, and decoupling.\n"
        "- Deep dive: Justifies SQL vs NoSQL, sharding keys, index design, replication lag, and cache invalidation.\n"
        "- Resilience: Identifies single points of failure (SPOFs), rate limiting, and failure blast radiuses.\n"
        "- Interviewer Guidance: Push for clear trade-off justifications. Challenge arbitrary technology selections "
        "('Why Cassandra over PostgreSQL? How do you partition keys?'). Expect candidate to drive the conversation."
    ),
    SeniorityLevel.STAFF.value: (
        "Candidate Level: STAFF / PRINCIPAL SOFTWARE ENGINEER (L6+ / Staff/Principal SDE)\n"
        "- Expected to operate with high architectural maturity, evaluating multi-year extensibility and org velocity.\n"
        "- Clarifies ambiguity, identifies unstated edge cases, and balances CAP theorem / PACELC trade-offs.\n"
        "- Focuses heavily on operational resilience: multi-region active-active, consensus protocols (Raft/Paxos), "
        "data loss tolerance (RPO/RTO), cascading failure prevention, and distributed transaction semantics (Saga).\n"
        "- Considers cost engineering: hardware constraints, network egress economics, and tiering cold vs hot storage.\n"
        "- Interviewer Guidance: Treat as a peer architecture review. Rigorously probe edge failure modes, partition "
        "tolerance, and distributed consistency. Demand rigorous rationale for every architectural constraint."
    ),
}


# -----------------------------------------------------------------------------
# Foundational System Meta-Instructions
# -----------------------------------------------------------------------------

BASE_INTERVIEWER_META_INSTRUCTIONS = """You are an elite Staff / Principal Software Engineer conducting a live, realistic technical System Design Interview at a top-tier technology company.

CORE INTERVIEWING PRINCIPLES:
1. INTERACTIVE DIALOGUE, NOT MONOLOGUES:
   - Keep your responses concise (1 to 3 short paragraphs maximum per turn).
   - Never dump entire architectural solutions or lecturing essays.
   - Ask 1 or at most 2 focused, probing questions at a time to keep conversational momentum.

2. SOCRATIC RIGOR & EVIDENCE-BASED PROBING:
   - When the candidate makes a technology choice (e.g., "We will use Kafka"), do not just accept it. Probe the reasoning:
     "Why Kafka over a lightweight message broker like RabbitMQ or SQS? What is your partitioning strategy?"
   - Challenge vague or hand-waving statements ("We will scale horizontally" -> "How do you handle state synchronization across scaled nodes?").

3. RESPECT THE ACTIVE STAGE BOUNDARIES:
   - Maintain focus on the objectives of the current interview stage.
   - If the candidate jumps ahead (e.g. designing database schemas during high-level requirements), gently acknowledge and redirect them back to the stage goal.

4. PROGRESSIVE HINTING:
   - If the candidate is stuck, do not give away the answer immediately.
   - Step 1: Provide a subtle conceptual nudge or ask a guiding question.
   - Step 2: If still struggling, narrow the scope of the problem.
   - Step 3: Offer concrete architectural options for the candidate to evaluate and select.

5. PROFESSIONAL & ENCOURAGING TONE:
   - Be constructive, professional, and collaborative while maintaining high technical standards.
   - Acknowledge strong insights when the candidate articulates effective trade-offs.
"""


# -----------------------------------------------------------------------------
# Context Data Container
# -----------------------------------------------------------------------------

@dataclass
class PromptContext:
    """Consolidated state and domain context used to hydrate interview prompts."""

    session_id: str
    candidate_level: str = SeniorityLevel.SENIOR.value
    problem_title: str = "Distributed System Design"
    problem_description: str = ""
    functional_requirements: list[str] = field(default_factory=list)
    non_functional_requirements: list[str] = field(default_factory=list)
    scale_benchmarks: dict[str, Any] = field(default_factory=dict)
    current_stage: str = InterviewStage.CLARIFICATION.value
    stage_turn_count: int = 0
    total_turns: int = 0
    dialogue_history: list[Any] = field(default_factory=list)
    artifacts: dict[str, Any] = field(default_factory=dict)
    calculations: list[dict[str, Any]] = field(default_factory=list)
    satisfied_criteria: list[str] = field(default_factory=list)
    candidate_name: str = "Candidate"


# -----------------------------------------------------------------------------
# Formatting Helpers
# -----------------------------------------------------------------------------

def format_seniority_expectations(level: str | SeniorityLevel) -> str:
    """Format candidate seniority level expectations for system prompt insertion."""
    lvl = level.value if isinstance(level, SeniorityLevel) else str(level).lower()
    return SENIORITY_EXPECTATIONS.get(lvl, SENIORITY_EXPECTATIONS[SeniorityLevel.SENIOR.value])


def format_dialogue_history(messages: list[Any], max_turns: int = 8) -> str:
    """Format recent turn-by-turn conversation messages into prompt-ready transcript."""
    if not messages:
        return "[No prior messages in this interview yet.]"

    recent = messages[-max_turns:]
    lines: list[str] = []

    for msg in recent:
        role = "System"
        content = ""

        if isinstance(msg, dict):
            role = str(msg.get("role") or msg.get("type") or "User").capitalize()
            content = str(msg.get("content", "")).strip()
        else:
            cls_name = msg.__class__.__name__.lower()
            if "human" in cls_name:
                role = "Candidate"
            elif "ai" in cls_name:
                role = "Interviewer"
            elif "system" in cls_name:
                role = "System"
            content = getattr(msg, "content", str(msg)).strip()

        if role.lower() in ("candidate", "human", "user"):
            speaker = "Candidate"
        elif role.lower() in ("interviewer", "ai", "assistant"):
            speaker = "Interviewer"
        else:
            speaker = "System"

        lines.append(f"{speaker}: {content}")

    return "\n\n".join(lines)


def format_artifact_context(artifacts: dict[str, Any]) -> str:
    """Format whiteboard canvas diagrams and architecture artifacts."""
    if not artifacts:
        return "[No architecture canvas or whiteboard artifacts submitted yet.]"

    formatted: list[str] = []

    mermaid = artifacts.get("mermaid_syntax") or artifacts.get("diagram")
    if mermaid:
        formatted.append(f"CURRENT WHITEBOARD DIAGRAM (Mermaid):\n```mermaid\n{mermaid}\n```")

    components = artifacts.get("components") or artifacts.get("nodes")
    if components and isinstance(components, list):
        comp_list = ", ".join(str(c.get("label", c)) if isinstance(c, dict) else str(c) for c in components)
        formatted.append(f"Identified Components: {comp_list}")

    apis = artifacts.get("api_endpoints") or artifacts.get("apis")
    if apis and isinstance(apis, list):
        api_lines = [
            f"- {a.get('method', 'POST')} {a.get('path', '/')}: {a.get('summary', '')}"
            if isinstance(a, dict) else f"- {a}"
            for a in apis
        ]
        formatted.append("Proposed API Contracts:\n" + "\n".join(api_lines))

    schemas = artifacts.get("data_schemas") or artifacts.get("schemas")
    if schemas and isinstance(schemas, list):
        schema_lines = [
            f"- Table: {s.get('table_name', 'entity')} (PK: {s.get('primary_key', 'id')})"
            if isinstance(s, dict) else f"- {s}"
            for s in schemas
        ]
        formatted.append("Proposed Database Schemas:\n" + "\n".join(schema_lines))

    return "\n\n".join(formatted) if formatted else "[Canvas artifacts present but empty.]"


def format_calculations(calculations: list[dict[str, Any]]) -> str:
    """Format candidate capacity estimation calculations."""
    if not calculations:
        return "[No quantitative calculations recorded yet.]"

    lines: list[str] = []
    for c in calculations:
        metric = c.get("metric_name") or c.get("name") or "Calculation"
        val = c.get("value") or c.get("calculated_value") or ""
        unit = c.get("unit") or ""
        assumptions = c.get("assumptions") or ""
        entry = f"- {metric}: {val} {unit}".strip()
        if assumptions:
            entry += f" (Assumptions: {assumptions})"
        lines.append(entry)

    return "\n".join(lines)


def format_problem_context(context: PromptContext) -> str:
    """Format problem statement, requirements, and scale benchmarks."""
    parts: list[str] = [
        f"PROBLEM TITLE: {context.problem_title}",
    ]

    if context.problem_description:
        parts.append(f"DESCRIPTION:\n{context.problem_description}")

    if context.functional_requirements:
        reqs = "\n".join(f"- {r}" for r in context.functional_requirements)
        parts.append(f"EXPECTED FUNCTIONAL REQUIREMENTS:\n{reqs}")

    if context.non_functional_requirements:
        reqs = "\n".join(f"- {r}" for r in context.non_functional_requirements)
        parts.append(f"EXPECTED NON-FUNCTIONAL REQUIREMENTS:\n{reqs}")

    if context.scale_benchmarks:
        benchmarks = "\n".join(f"- {k}: {v}" for k, v in context.scale_benchmarks.items())
        parts.append(f"SCALE BENCHMARKS & CONSTRAINTS:\n{benchmarks}")

    return "\n\n".join(parts)


# -----------------------------------------------------------------------------
# System Prompt Renderers & Builder
# -----------------------------------------------------------------------------

def render_base_system_prompt(
    context: PromptContext,
    persona_prompt: str = "",
) -> str:
    """Render comprehensive foundation system prompt for the interview agent.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.

    Returns:
        Fully hydrated system prompt ready for LLM invocation.
    """
    seniority_section = format_seniority_expectations(context.candidate_level)
    problem_section = format_problem_context(context)
    artifact_section = format_artifact_context(context.artifacts)
    calc_section = format_calculations(context.calculations)

    persona_section = (
        f"\nINTERVIEWER PERSONA STYLE:\n{persona_prompt.strip()}\n"
        if persona_prompt.strip()
        else ""
    )

    return f"""{BASE_INTERVIEWER_META_INSTRUCTIONS}
{persona_section}
================================================================================
INTERVIEW EXECUTION CONTEXT
================================================================================
Active Stage: {context.current_stage.upper()}
Stage Turn Count: {context.stage_turn_count} (Total Interview Turns: {context.total_turns})
Candidate Name: {context.candidate_name}

{seniority_section}

================================================================================
PROBLEM SPECIFICATION & GROUND TRUTH BENCHMARKS
================================================================================
{problem_section}

================================================================================
CANDIDATE ARTIFACTS & CAPACITY CALCULATIONS
================================================================================
Capacity Math:
{calc_section}

Whiteboard / Architecture Canvas:
{artifact_section}
""".strip()


class BasePromptBuilder:
    """Fluent builder for composing multi-tiered LangGraph interview prompts."""

    def __init__(self, context: PromptContext) -> None:
        self.context = context
        self._persona_prompt: str = ""
        self._stage_prompt: str = ""
        self._guard_instructions: list[str] = []
        self._custom_sections: dict[str, str] = {}

    def with_persona(self, persona_prompt: str) -> BasePromptBuilder:
        """Set interviewer persona instructions."""
        self._persona_prompt = persona_prompt.strip()
        return self

    def with_stage_instruction(self, stage_prompt: str) -> BasePromptBuilder:
        """Set active stage-specific behavioral guidelines."""
        self._stage_prompt = stage_prompt.strip()
        return self

    def with_guard_instructions(self, guards: list[str]) -> BasePromptBuilder:
        """Attach active guard directives (e.g. pacing warning, missing criteria)."""
        self._guard_instructions.extend(guards)
        return self

    def with_section(self, header: str, content: str) -> BasePromptBuilder:
        """Add arbitrary custom context section."""
        if content.strip():
            self._custom_sections[header] = content.strip()
        return self

    def build_system_prompt(self) -> str:
        """Compile complete system prompt string."""
        base_prompt = render_base_system_prompt(self.context, persona_prompt=self._persona_prompt)
        sections: list[str] = [base_prompt]

        if self._stage_prompt:
            sections.append(
                f"================================================================================\n"
                f"STAGE SPECIFIC DIRECTIVES ({self.context.current_stage.upper()})\n"
                f"================================================================================\n"
                f"{self._stage_prompt}"
            )

        if self._guard_instructions:
            guards_text = "\n".join(f"- {g}" for g in self._guard_instructions)
            sections.append(
                f"================================================================================\n"
                f"ACTIVE PACING & GUARD ALERTS\n"
                f"================================================================================\n"
                f"{guards_text}"
            )

        for header, content in self._custom_sections.items():
            sections.append(
                f"================================================================================\n"
                f"{header.upper()}\n"
                f"================================================================================\n"
                f"{content}"
            )

        return "\n\n".join(sections)

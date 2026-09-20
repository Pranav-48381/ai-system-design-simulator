"""System Design Interview Simulator - Stage Progression & Transition Engine.

Defines interview stage sequencing, prerequisites, time budgeting, turn thresholds,
and transition validation rules governing the candidate journey through the
system design interview state machine.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Final

from app.core.constants import (
    INTERVIEW_STAGE_DESCRIPTIONS,
    INTERVIEW_STAGE_ORDER,
    INTERVIEW_STAGE_TITLES,
    InterviewStage,
)

# Ordered sequence of the 6 interview stages
STAGE_SEQUENCE: Final[list[InterviewStage]] = INTERVIEW_STAGE_ORDER

# Stage prerequisite dependencies
STAGE_PREREQUISITES: Final[dict[InterviewStage, list[InterviewStage]]] = {
    InterviewStage.CLARIFICATION: [],
    InterviewStage.ESTIMATION: [InterviewStage.CLARIFICATION],
    InterviewStage.ARCHITECTURE: [
        InterviewStage.CLARIFICATION,
        InterviewStage.ESTIMATION,
    ],
    InterviewStage.DEEP_DIVE: [InterviewStage.ARCHITECTURE],
    InterviewStage.BOTTLENECK: [
        InterviewStage.ARCHITECTURE,
        InterviewStage.DEEP_DIVE,
    ],
    InterviewStage.EVALUATION: [
        InterviewStage.BOTTLENECK,
    ],
}

# Standard 45-minute interview time allocations (in minutes)
STAGE_TIME_ALLOCATIONS: Final[dict[InterviewStage, int]] = {
    InterviewStage.CLARIFICATION: 5,
    InterviewStage.ESTIMATION: 5,
    InterviewStage.ARCHITECTURE: 12,
    InterviewStage.DEEP_DIVE: 12,
    InterviewStage.BOTTLENECK: 6,
    InterviewStage.EVALUATION: 5,
}

# Dialogue turn boundaries per stage to balance depth against pacing
STAGE_MINIMUM_TURNS: Final[dict[InterviewStage, int]] = {
    InterviewStage.CLARIFICATION: 2,
    InterviewStage.ESTIMATION: 1,
    InterviewStage.ARCHITECTURE: 2,
    InterviewStage.DEEP_DIVE: 2,
    InterviewStage.BOTTLENECK: 2,
    InterviewStage.EVALUATION: 1,
}

STAGE_MAXIMUM_TURNS: Final[dict[InterviewStage, int]] = {
    InterviewStage.CLARIFICATION: 8,
    InterviewStage.ESTIMATION: 6,
    InterviewStage.ARCHITECTURE: 10,
    InterviewStage.DEEP_DIVE: 10,
    InterviewStage.BOTTLENECK: 8,
    InterviewStage.EVALUATION: 4,
}


@dataclass(frozen=True)
class StageDefinition:
    """Immutable specification for an interview lifecycle stage."""

    stage: InterviewStage
    title: str
    description: str
    target_duration_minutes: int
    min_turns: int
    max_turns: int
    prerequisites: list[InterviewStage] = field(default_factory=list)
    key_competencies: list[str] = field(default_factory=list)


# Stage competency mappings
_STAGE_COMPETENCIES: Final[dict[InterviewStage, list[str]]] = {
    InterviewStage.CLARIFICATION: [
        "Functional requirements extraction",
        "Non-functional SLAs & SLOs",
        "System constraint identification",
        "Boundary scoping",
    ],
    InterviewStage.ESTIMATION: [
        "QPS & throughput estimation",
        "Storage volume & growth math",
        "Network bandwidth calculation",
        "Cache memory sizing (80/20 rule)",
    ],
    InterviewStage.ARCHITECTURE: [
        "API contract design",
        "Component decomposition",
        "Client-service communication patterns",
        "End-to-end data pipeline flow",
    ],
    InterviewStage.DEEP_DIVE: [
        "Data model & schema normalization",
        "Partitioning / Sharding key selection",
        "Replication & consensus models",
        "Caching tier invalidation patterns",
    ],
    InterviewStage.BOTTLENECK: [
        "Single points of failure (SPOFs)",
        "Rate limiting & load shedding",
        "Circuit breakers & bulkhead isolation",
        "Disaster recovery & failover topologies",
    ],
    InterviewStage.EVALUATION: [
        "Multi-pillar performance rubric synthesis",
        "Hiring level calibration",
        "Actionable technical growth vectors",
    ],
}


def get_stage_definition(stage: InterviewStage | str) -> StageDefinition:
    """Retrieve the rich `StageDefinition` for a given interview stage."""
    parsed_stage = InterviewStage(stage)
    return StageDefinition(
        stage=parsed_stage,
        title=INTERVIEW_STAGE_TITLES[parsed_stage],
        description=INTERVIEW_STAGE_DESCRIPTIONS[parsed_stage],
        target_duration_minutes=STAGE_TIME_ALLOCATIONS[parsed_stage],
        min_turns=STAGE_MINIMUM_TURNS[parsed_stage],
        max_turns=STAGE_MAXIMUM_TURNS[parsed_stage],
        prerequisites=list(STAGE_PREREQUISITES[parsed_stage]),
        key_competencies=list(_STAGE_COMPETENCIES[parsed_stage]),
    )


def get_next_stage(current: InterviewStage | str) -> InterviewStage | None:
    """Determine the sequential successor stage, or None if at the terminal stage."""
    parsed = InterviewStage(current)
    try:
        current_index = STAGE_SEQUENCE.index(parsed)
        if current_index + 1 < len(STAGE_SEQUENCE):
            return STAGE_SEQUENCE[current_index + 1]
        return None
    except ValueError:
        return None


def get_previous_stage(current: InterviewStage | str) -> InterviewStage | None:
    """Determine the sequential predecessor stage, or None if at the initial stage."""
    parsed = InterviewStage(current)
    try:
        current_index = STAGE_SEQUENCE.index(parsed)
        if current_index > 0:
            return STAGE_SEQUENCE[current_index - 1]
        return None
    except ValueError:
        return None


def get_missing_prerequisites(
    target_stage: InterviewStage | str,
    completed_stages: Sequence[str | InterviewStage],
) -> list[InterviewStage]:
    """Return a list of prerequisite stages not yet satisfied for the target stage."""
    target = InterviewStage(target_stage)
    completed_set = {
        InterviewStage(s) if isinstance(s, str) else s for s in completed_stages
    }
    prereqs = STAGE_PREREQUISITES.get(target, [])
    return [p for p in prereqs if p not in completed_set]


def is_stage_accessible(
    target_stage: InterviewStage | str,
    completed_stages: Sequence[str | InterviewStage],
) -> bool:
    """Verify whether all prerequisite stages have been completed for a target stage."""
    return len(get_missing_prerequisites(target_stage, completed_stages)) == 0


def validate_stage_transition(
    current_stage: InterviewStage | str,
    target_stage: InterviewStage | str,
    completed_stages: Sequence[str | InterviewStage],
) -> tuple[bool, str | None]:
    """Validate whether transitioning from current to target stage is permitted.

    Returns:
        (is_valid, error_reason)
    """
    curr = InterviewStage(current_stage)
    target = InterviewStage(target_stage)

    if curr == target:
        return True, None

    # Check if target is already accessible via satisfied prerequisites
    missing = get_missing_prerequisites(target, completed_stages)
    # The current stage could be satisfying the missing prereq upon advancement
    unmet = [m for m in missing if m != curr]
    if unmet:
        unmet_names = ", ".join(m.value for m in unmet)
        return False, f"Target stage '{target.value}' requires completion of: {unmet_names}"

    return True, None

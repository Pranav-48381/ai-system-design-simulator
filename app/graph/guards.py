"""System Design Interview Simulator - Stage Exit Criteria Guards.

Implements stage exit validation rules, pacing limits, turn thresholds,
prerequisite enforcement, and rubric criteria satisfaction checks that
govern whether an interview stage can advance or requires further turns.
"""

from dataclasses import dataclass, field
import time
from typing import Any, Final

from app.core.constants import InterviewStage
from app.graph.stages import (
    STAGE_MAXIMUM_TURNS,
    STAGE_MINIMUM_TURNS,
    STAGE_PREREQUISITES,
    STAGE_TIME_ALLOCATIONS,
    get_stage_definition,
    is_stage_accessible,
)
from app.graph.state import InterviewState


# Standard key criteria required for each stage to consider it organically satisfied
STAGE_REQUIRED_CRITERIA: Final[dict[InterviewStage, list[str]]] = {
    InterviewStage.CLARIFICATION: [
        "functional_requirements",
        "non_functional_requirements",
        "scale_assumptions",
    ],
    InterviewStage.ESTIMATION: [
        "traffic_qps",
        "storage_capacity",
        "bandwidth_throughput",
    ],
    InterviewStage.ARCHITECTURE: [
        "api_endpoints",
        "core_components",
        "high_level_data_flow",
    ],
    InterviewStage.DEEP_DIVE: [
        "data_storage_schema",
        "caching_strategy",
        "concurrency_or_sharding",
    ],
    InterviewStage.BOTTLENECK: [
        "single_points_of_failure",
        "fault_tolerance_recovery",
        "rate_limiting_resilience",
    ],
    InterviewStage.EVALUATION: [
        "rubric_scoring_complete",
        "debrief_feedback_generated",
    ],
}


@dataclass(frozen=True)
class StageExitGuardResult:
    """Evaluation result from testing stage exit criteria."""

    can_exit: bool
    stage: InterviewStage
    reason: str
    recommended_action: str
    missing_criteria: list[str] = field(default_factory=list)
    turn_count: int = 0
    min_turns: int = 0
    max_turns: int = 0
    is_min_turns_met: bool = False
    is_max_turns_exceeded: bool = False
    is_time_limit_exceeded: bool = False
    elapsed_seconds: float = 0.0
    allocated_seconds: float = 0.0


def check_min_turn_guard(state: InterviewState | dict[str, Any]) -> bool:
    """Check if the candidate has satisfied the minimum turn threshold for the current stage.

    Args:
        state: Current interview state dictionary.

    Returns:
        True if minimum turn threshold is met, False otherwise.
    """
    stage_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    stage = InterviewStage(stage_val)
    min_turns = STAGE_MINIMUM_TURNS.get(stage, 1)
    turn_count = int(state.get("stage_turn_count", 0))
    return turn_count >= min_turns


def check_max_turn_guard(state: InterviewState | dict[str, Any]) -> bool:
    """Check if the candidate has reached or exceeded the maximum turn threshold.

    Args:
        state: Current interview state dictionary.

    Returns:
        True if max turns reached or exceeded, False otherwise.
    """
    stage_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    stage = InterviewStage(stage_val)
    max_turns = STAGE_MAXIMUM_TURNS.get(stage, 10)
    turn_count = int(state.get("stage_turn_count", 0))
    return turn_count >= max_turns


def check_pacing_guard(state: InterviewState | dict[str, Any]) -> tuple[bool, float, float]:
    """Evaluate whether the current stage has exceeded its allocated time budget.

    Args:
        state: Current interview state dictionary.

    Returns:
        Tuple of (is_overtime, elapsed_seconds, allocated_seconds).
    """
    stage_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    stage = InterviewStage(stage_val)
    allocated_minutes = STAGE_TIME_ALLOCATIONS.get(stage, 10)
    allocated_seconds = float(allocated_minutes * 60)

    now = time.time()
    start_time = float(state.get("stage_start_time", now))
    elapsed_seconds = max(0.0, now - start_time)

    # Consider overtime if elapsed time exceeds 120% of allocated budget
    is_overtime = elapsed_seconds >= (allocated_seconds * 1.2)
    return is_overtime, elapsed_seconds, allocated_seconds


def check_stage_prerequisites_guard(
    state: InterviewState | dict[str, Any],
    target_stage: InterviewStage | str,
) -> tuple[bool, list[InterviewStage]]:
    """Verify that all prerequisite stages have been completed before advancing.

    Args:
        state: Current interview state dictionary.
        target_stage: Target stage to transition to.

    Returns:
        Tuple of (is_valid, missing_prerequisites).
    """
    target = target_stage if isinstance(target_stage, InterviewStage) else InterviewStage(str(target_stage))
    completed_str_list = state.get("completed_stages", [])
    completed_stages = [InterviewStage(s) for s in completed_str_list if s in InterviewStage._value2member_map_]

    required = STAGE_PREREQUISITES.get(target, [])
    missing = [req for req in required if req not in completed_stages]
    return (len(missing) == 0, missing)


def get_missing_criteria(
    state: InterviewState | dict[str, Any],
    stage: InterviewStage | None = None,
) -> list[str]:
    """Identify which required criteria for a stage have not yet been recorded as satisfied.

    Args:
        state: Current interview state dictionary.
        stage: Target stage to check, defaulting to state['current_stage'].

    Returns:
        List of missing criteria string identifiers.
    """
    current_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    target_stage = stage or InterviewStage(current_val)
    required = STAGE_REQUIRED_CRITERIA.get(target_stage, [])

    satisfied_map: dict[str, list[str]] = state.get("stage_criteria_satisfied", {})
    satisfied_list = [c.lower() for c in satisfied_map.get(target_stage.value, [])]

    # Special stage content heuristic checks
    missing: list[str] = []
    for req in required:
        # Check if criterion was explicitly registered
        if any(req in s or s in req for s in satisfied_list):
            continue

        # Heuristic checks based on state data structures
        if target_stage == InterviewStage.ESTIMATION and req == "traffic_qps":
            calcs = state.get("calculations", [])
            if any("qps" in str(c.get("name", "")).lower() or "throughput" in str(c.get("name", "")).lower() for c in calcs):
                continue
        elif target_stage == InterviewStage.ESTIMATION and req == "storage_capacity":
            calcs = state.get("calculations", [])
            if any("storage" in str(c.get("name", "")).lower() or "tb" in str(c.get("unit", "")).lower() for c in calcs):
                continue
        elif target_stage == InterviewStage.ARCHITECTURE and req == "high_level_data_flow":
            artifacts = state.get("active_artifacts", {})
            if "canvas" in artifacts or "architecture_diagram" in artifacts:
                continue

        missing.append(req)

    return missing


def evaluate_stage_exit_guards(
    state: InterviewState | dict[str, Any],
    *,
    force_transition: bool = False,
) -> StageExitGuardResult:
    """Master evaluator checking all entry/exit guards for advancing the current stage.

    Evaluates:
    1. Force transition flag (e.g. manual override or timeout node).
    2. Minimum turn constraints to ensure meaningful interaction.
    3. Maximum turn constraints and pacing thresholds.
    4. Rubric criteria coverage.
    5. Candidate explicit intent to submit stage.

    Args:
        state: Current interview state dictionary.
        force_transition: Explicit flag overriding criteria checks (e.g., from slash command).

    Returns:
        StageExitGuardResult describing decision, reasons, and recommended action.
    """
    stage_val = state.get("current_stage", InterviewStage.CLARIFICATION.value)
    stage = InterviewStage(stage_val)
    stage_def = get_stage_definition(stage)

    turn_count = int(state.get("stage_turn_count", 0))
    min_turns = stage_def.min_turns
    max_turns = stage_def.max_turns

    is_min_turns_met = turn_count >= min_turns
    is_max_turns_exceeded = turn_count >= max_turns
    is_overtime, elapsed_seconds, allocated_seconds = check_pacing_guard(state)

    missing = get_missing_criteria(state, stage)
    candidate_intent = str(state.get("candidate_intent") or "").lower()
    is_candidate_requesting_advance = candidate_intent in (
        "submit_stage",
        "advance_stage",
        "next_stage",
        "ready_to_move_on",
    )

    # 1. Explicit force transition override
    if force_transition:
        return StageExitGuardResult(
            can_exit=True,
            stage=stage,
            reason="Stage transition explicitly forced by orchestrator.",
            recommended_action="advance_stage",
            missing_criteria=missing,
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=is_min_turns_met,
            is_max_turns_exceeded=is_max_turns_exceeded,
            is_time_limit_exceeded=is_overtime,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 2. Maximum turn threshold exceeded - force advance to prevent getting stuck
    if is_max_turns_exceeded:
        return StageExitGuardResult(
            can_exit=True,
            stage=stage,
            reason=f"Stage reached maximum turn threshold ({turn_count}/{max_turns}). Advancing for interview pacing.",
            recommended_action="advance_stage_with_pacing_warning",
            missing_criteria=missing,
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=True,
            is_max_turns_exceeded=True,
            is_time_limit_exceeded=is_overtime,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 3. Minimum turn threshold NOT met - cannot advance yet
    if not is_min_turns_met:
        return StageExitGuardResult(
            can_exit=False,
            stage=stage,
            reason=f"Candidate has completed {turn_count}/{min_turns} required turns for {stage.value}.",
            recommended_action="continue_stage_probing",
            missing_criteria=missing,
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=False,
            is_max_turns_exceeded=False,
            is_time_limit_exceeded=is_overtime,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 4. Candidate requested advance and minimum turns met
    if is_candidate_requesting_advance:
        if missing:
            # Candidate wants to advance but missed some criteria - allow with soft note
            return StageExitGuardResult(
                can_exit=True,
                stage=stage,
                reason=f"Candidate requested transition; minimum turns met ({turn_count} turns), though criteria incomplete.",
                recommended_action="advance_stage_with_feedback",
                missing_criteria=missing,
                turn_count=turn_count,
                min_turns=min_turns,
                max_turns=max_turns,
                is_min_turns_met=True,
                is_max_turns_exceeded=False,
                is_time_limit_exceeded=is_overtime,
                elapsed_seconds=elapsed_seconds,
                allocated_seconds=allocated_seconds,
            )
        return StageExitGuardResult(
            can_exit=True,
            stage=stage,
            reason="Candidate requested transition and all key criteria are satisfied.",
            recommended_action="advance_stage",
            missing_criteria=[],
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=True,
            is_max_turns_exceeded=False,
            is_time_limit_exceeded=is_overtime,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 5. All criteria satisfied organically
    if not missing:
        return StageExitGuardResult(
            can_exit=True,
            stage=stage,
            reason=f"All key criteria for stage {stage.value} satisfied successfully.",
            recommended_action="suggest_advancement",
            missing_criteria=[],
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=True,
            is_max_turns_exceeded=False,
            is_time_limit_exceeded=is_overtime,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 6. Budget overtime warning
    if is_overtime:
        return StageExitGuardResult(
            can_exit=True,
            stage=stage,
            reason=f"Stage allocated time ({allocated_seconds / 60:.0f}m) exceeded. Recommend transitioning.",
            recommended_action="prompt_transition_or_offer_hint",
            missing_criteria=missing,
            turn_count=turn_count,
            min_turns=min_turns,
            max_turns=max_turns,
            is_min_turns_met=True,
            is_max_turns_exceeded=False,
            is_time_limit_exceeded=True,
            elapsed_seconds=elapsed_seconds,
            allocated_seconds=allocated_seconds,
        )

    # 7. Default: continue probing current stage
    return StageExitGuardResult(
        can_exit=False,
        stage=stage,
        reason=f"Stage in progress. Missing criteria: {', '.join(missing)}.",
        recommended_action="prompt_missing_criteria",
        missing_criteria=missing,
        turn_count=turn_count,
        min_turns=min_turns,
        max_turns=max_turns,
        is_min_turns_met=True,
        is_max_turns_exceeded=False,
        is_time_limit_exceeded=False,
        elapsed_seconds=elapsed_seconds,
        allocated_seconds=allocated_seconds,
    )

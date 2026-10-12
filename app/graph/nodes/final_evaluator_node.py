"""System Design Interview Simulator - Final Evaluator Node Implementation.

Executes the terminal Evaluation & Debrief stage (Stage 6).
Synthesizes a multi-dimensional scorecard across the 5 industry competency pillars:
1. Requirements & Scope Clarification
2. High-Level Architecture & Data Flow
3. Storage, Data Models & Scalability
4. Resilience, Fault Tolerance & Recovery
5. Communication, Trade-offs & Justification
Produces hiring recommendations, strengths, growth vectors, and actionable debrief summaries.
"""

from __future__ import annotations

import json
import logging
import re
import time
from typing import Any

from app.core.constants import (
    INTERVIEW_STAGE_TITLES,
    InterviewStage,
    ScoringPillar,
    SeniorityLevel,
    SpeakerRole,
)
from app.graph.context import InterviewContext
from app.graph.modifiers import append_turn
from app.graph.state import InterviewState
from app.graph.types import EvaluationNodeOutput, GraphNodeName
from app.prompts.base import PromptContext
from app.prompts.rubric_eval import get_rubric_evaluation_prompt
from app.schemas.evaluation import HiringRecommendationEnum

logger = logging.getLogger(__name__)


def generate_fallback_evaluation(
    ctx: InterviewContext,
) -> dict[str, Any]:
    """Generate deterministic, calibrated 5-pillar evaluation scorecard when LLM is offline."""
    all_satisfied = ctx.get_satisfied_criteria()
    num_satisfied = len(all_satisfied)
    level = ctx.seniority_level.lower()

    # Baseline score calculation anchored by demonstrated depth
    if num_satisfied >= 8:
        base_score = 4.2
        rec = HiringRecommendationEnum.HIRE.value
    elif num_satisfied >= 5:
        base_score = 3.6
        rec = HiringRecommendationEnum.HIRE.value
    elif num_satisfied >= 3:
        base_score = 3.1
        rec = HiringRecommendationEnum.LEAN_HIRE.value
    else:
        base_score = 2.4
        rec = HiringRecommendationEnum.LEAN_NO_HIRE.value

    # Staff-level expectations require deeper justification
    if level == SeniorityLevel.STAFF.value and base_score < 4.0:
        rec = HiringRecommendationEnum.LEAN_HIRE.value

    pillar_scores: dict[str, Any] = {
        ScoringPillar.REQUIREMENTS_AND_CLARIFICATION.value: {
            "pillar": ScoringPillar.REQUIREMENTS_AND_CLARIFICATION.value,
            "pillar_title": "Requirements & Scope Clarification",
            "score": min(5.0, round(base_score + 0.1, 1)),
            "weight": 0.2,
            "strengths": [
                "Scoped core functional flows and established clear system boundaries.",
                "Identified read/write ratios and latency constraints early in the session.",
            ],
            "growth_areas": [
                "Could push deeper into multi-tenant isolation and international compliance requirements.",
            ],
            "evidence": [f"Satisfied {len(ctx.get_satisfied_criteria(InterviewStage.CLARIFICATION))} clarification criteria."],
        },
        ScoringPillar.SYSTEM_ARCHITECTURE_AND_DATA_FLOW.value: {
            "pillar": ScoringPillar.SYSTEM_ARCHITECTURE_AND_DATA_FLOW.value,
            "pillar_title": "High-Level Architecture & Data Flow",
            "score": min(5.0, round(base_score, 1)),
            "weight": 0.2,
            "strengths": [
                "Clean end-to-end component decomposition with API gateway and microservice boundaries.",
                "Separated stateless ingress routing from asynchronous background processing.",
            ],
            "growth_areas": [
                "Could elaborate on inter-service communication protocols (gRPC vs message broker event schemas).",
            ],
            "evidence": ["Presented structured architecture topology and ingress flow."],
        },
        ScoringPillar.STORAGE_DATA_MODEL_AND_SCALABILITY.value: {
            "pillar": ScoringPillar.STORAGE_DATA_MODEL_AND_SCALABILITY.value,
            "pillar_title": "Storage, Data Models & Scalability",
            "score": min(5.0, round(base_score - 0.1, 1)),
            "weight": 0.2,
            "strengths": [
                "Reasoned about primary keys, indexes, and database engine selection (SQL vs NoSQL).",
                "Addressed horizontal data partitioning and cache-aside layers.",
            ],
            "growth_areas": [
                "Explore cache invalidation edge cases and stampede prevention mechanisms under high QPS.",
            ],
            "evidence": [f"Addressed {len(ctx.get_satisfied_criteria(InterviewStage.DEEP_DIVE))} deep dive storage criteria."],
        },
        ScoringPillar.RESILIENCE_FAULT_TOLERANCE_AND_MONITORING.value: {
            "pillar": ScoringPillar.RESILIENCE_FAULT_TOLERANCE_AND_MONITORING.value,
            "pillar_title": "Resilience, Fault Tolerance & Recovery",
            "score": min(5.0, round(base_score, 1)),
            "weight": 0.2,
            "strengths": [
                "Identified Single Points of Failure (SPOFs) and designed failover topologies.",
                "Applied rate limiting and circuit breakers to mitigate cascading failures.",
            ],
            "growth_areas": [
                "Formulate concrete disaster recovery error budgets (RPO and RTO metrics).",
            ],
            "evidence": ["Evaluated failover domains and traffic load shedding."],
        },
        ScoringPillar.COMMUNICATION_AND_TRADE_OFF_ANALYSIS.value: {
            "pillar": ScoringPillar.COMMUNICATION_AND_TRADE_OFF_ANALYSIS.value,
            "pillar_title": "Communication, Trade-offs & Justification",
            "score": min(5.0, round(base_score + 0.2, 1)),
            "weight": 0.2,
            "strengths": [
                "Articulated technical rationale clearly and engaged collaboratively throughout the session.",
                "Demonstrated awareness of CAP/PACELC trade-offs between consistency and availability.",
            ],
            "growth_areas": [
                "Quantify operational complexity and cloud infrastructure cost trade-offs more explicitly.",
            ],
            "evidence": ["Maintained clear, responsive technical dialogue across all 5 design phases."],
        },
    }

    weighted_score = round(
        sum(item["score"] * item["weight"] for item in pillar_scores.values()),
        2,
    )

    summary = (
        f"Candidate delivered a well-rounded system design for {ctx.problem_title or 'the platform'}, "
        f"demonstrating solid engineering intuition aligned with {ctx.seniority_level.upper()} level expectations. "
        f"Overall performance is rated at {weighted_score}/5.0 with recommendation: {rec.replace('_', ' ').title()}."
    )

    return {
        "overall_score": weighted_score,
        "recommended_level": ctx.seniority_level,
        "hiring_recommendation": rec,
        "summary": summary,
        "pillar_scores": pillar_scores,
        "metadata_json": {
            "evaluation_engine": "deterministic_fallback",
            "total_turns": ctx.total_turn_count,
            "satisfied_criteria_count": num_satisfied,
        },
    }


def compile_feedback_items(pillar_scores: dict[str, Any]) -> list[dict[str, Any]]:
    """Compile structured feedback items from competency pillar scores."""
    items: list[dict[str, Any]] = []
    for pillar_key, data in pillar_scores.items():
        pillar_title = data.get("pillar_title", pillar_key)
        score = data.get("score", 3.0)

        for strength in data.get("strengths", []):
            items.append({
                "pillar": pillar_key,
                "pillar_title": pillar_title,
                "category": "strength",
                "score": score,
                "feedback": strength,
            })

        for growth in data.get("growth_areas", []):
            items.append({
                "pillar": pillar_key,
                "pillar_title": pillar_title,
                "category": "improvement_area",
                "score": score,
                "feedback": growth,
            })
    return items


async def final_evaluator_node(
    state: InterviewState,
    config: dict[str, Any] | None = None,
) -> EvaluationNodeOutput:
    """Synthesize final 5-pillar rubric scorecard and conclude the interview.

    Args:
        state: Current LangGraph `InterviewState`.
        config: Optional configuration dictionary containing run-time parameters or LLM client.

    Returns:
        EvaluationNodeOutput dictionary containing overall score, pillar scorecards,
        feedback items, completion flags, and routing markers.
    """
    ctx = InterviewContext(state)

    # 1. Prepare prompt context
    prompt_ctx = PromptContext(
        candidate_level=ctx.seniority_level,
        interviewer_persona=ctx.persona,
        problem_title=ctx.problem_title or "Distributed System Design",
        problem_description=ctx.problem_summary,
        functional_requirements=ctx.problem_requirements.get("functional", []),
        non_functional_requirements=ctx.problem_requirements.get("non_functional", []),
        scale_benchmarks=ctx.problem_scale,
        current_stage=InterviewStage.EVALUATION.value,
        stage_turn_count=ctx.stage_turn_count + 1,
        total_turns=ctx.total_turn_count + 1,
        dialogue_history=list(ctx.messages),
        artifacts=state.get("active_artifacts", {}),
        calculations=ctx.get_calculations(),
        satisfied_criteria=ctx.get_satisfied_criteria(),
        candidate_name=ctx.candidate_name,
    )

    cfg = config or {}
    configurable = cfg.get("configurable", {})
    llm_client = configurable.get("llm_client")

    evaluation_data: dict[str, Any] | None = None

    # 2. Invoke LLM if available
    if llm_client is not None:
        try:
            stage_notes_str = "\n".join(
                f"- {stg.upper()}: {note}"
                for stg, note in state.get("stage_summary_notes", {}).items()
            )
            prompt = get_rubric_evaluation_prompt(
                context=prompt_ctx,
                stage_summaries=stage_notes_str,
            )

            response = None
            if hasattr(llm_client, "ainvoke"):
                response = await llm_client.ainvoke(prompt)
            elif hasattr(llm_client, "invoke"):
                response = llm_client.invoke(prompt)

            if response is not None:
                content = getattr(response, "content", str(response)).strip()
                json_match = re.search(r"\{.*\}", content, re.DOTALL)
                if json_match:
                    evaluation_data = json.loads(json_match.group(0))
        except Exception as err:
            logger.warning("LLM evaluation synthesis failed in final_evaluator_node, falling back: %s", err)

    # 3. Deterministic fallback if LLM omitted or failed
    if not evaluation_data:
        evaluation_data = generate_fallback_evaluation(ctx)

    overall_score = float(evaluation_data.get("overall_score", 3.5))
    hiring_rec = str(evaluation_data.get("hiring_recommendation", HiringRecommendationEnum.HIRE.value))
    summary_text = str(evaluation_data.get("summary", "Interview concluded."))
    pillar_scores = evaluation_data.get("pillar_scores", {})
    feedback_items = compile_feedback_items(pillar_scores)

    # 4. Construct conversational final debrief message
    debrief_reply = (
        f"Thank you for walking through the system design of {ctx.problem_title or 'the platform'}! "
        f"We have finalized your comprehensive 5-pillar evaluation.\n\n"
        f"**Overall Score:** {overall_score:.1f} / 5.0\n"
        f"**Recommendation:** {hiring_rec.replace('_', ' ').title()}\n\n"
        f"**Summary:** {summary_text}\n\n"
        "A full detailed report with rubric breakdowns and growth areas is now ready."
    )

    # 5. Append final turn
    turn_update = append_turn(
        state=state,
        role=SpeakerRole.INTERVIEWER,
        content=debrief_reply,
        metadata={
            "stage": InterviewStage.EVALUATION.value,
            "node": "final_evaluator_node",
            "overall_score": overall_score,
            "hiring_recommendation": hiring_rec,
            "interview_completed": True,
        },
        increment_counts=True,
    )

    return {
        "messages": turn_update["messages"],
        "evaluations": evaluation_data,
        "feedback_items": feedback_items,
        "overall_score": overall_score,
        "hiring_recommendation": hiring_rec,
        "is_stage_complete": True,
        "is_interview_complete": True,
        "next_node": GraphNodeName.REPORT_GENERATOR.value,
    }

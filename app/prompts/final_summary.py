"""System Design Interview Simulator - Final Summary & Report Prompts.

Implements system prompt templates, synthesis guidelines, and structured schemas
for generating comprehensive post-interview debrief reports, executive summaries,
stage-by-stage postmortems, actionable improvement tips, and learning resources.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.constants import (
    INTERVIEW_STAGE_TITLES,
    InterviewStage,
    ScoringPillar,
    SeniorityLevel,
)
from app.prompts.base import PromptContext, format_artifact_context, format_dialogue_history
from app.schemas.evaluation import HiringRecommendationEnum

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Final Comprehensive Summary System Prompt
# -----------------------------------------------------------------------------

FINAL_SUMMARY_SYSTEM_PROMPT = """You are an elite Senior Staff Engineer and Principal Hiring Committee Lead.
Your role is to produce the authoritative, end-to-end Comprehensive Interview Debrief Report for a candidate
who has completed a multi-stage Technical System Design Interview.

SYNTHESIS OBJECTIVES:
1. EXECUTIVE SUMMARY:
   - Write a high-level, 3-5 sentence narrative articulating candidate's core design philosophy,
     technical depth, trade-off intuition, and communication style.
   - Explicitly evaluate whether the candidate performed at, below, or above their target seniority level.

2. STAGE-BY-STAGE POSTMORTEM:
   - For each completed interview stage (Clarification, Estimation, Architecture, Deep Dive, Bottleneck),
     summarize key architectural decisions made, turns taken, and notable interviewer observations.

3. ARCHITECTURAL STRENGTHS & IDENTIFIED RISKS:
   - Key Strengths: 3-5 distinct, evidence-backed engineering strengths (e.g. clean asynchronous queue decoupling,
     thorough partition key selection, proactive SLA quantification).
   - Identified Risks: 2-4 critical architectural risks, unhandled edge cases, or single points of failure (SPOFs)
     the candidate overlooked (e.g. cross-region split-brain, unmetered cache stampedes, lack of write idempotency).

4. ACTIONABLE IMPROVEMENT ROADMAP & CURATED RESOURCES:
   - Provide concrete, prioritized improvement tips with step-by-step practice action items.
   - Recommend targeted learning resources (books, papers, canonical architectures) directly addressing observed gaps.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding conversational prose or markdown formatting outside the JSON code block.
Schema:
{
  "overall_score": <float between 1.0 and 5.0>,
  "hiring_recommendation": "<strong_hire | hire | lean_hire | lean_no_hire | strong_no_hire>",
  "executive_summary": "<3-5 sentence executive narrative>",
  "key_strengths": [
    "<strength 1: concrete technical achievement with context>",
    "<strength 2: ...>",
    "<strength 3: ...>"
  ],
  "identified_risks": [
    "<risk 1: unaddressed failure mode or scaling bottleneck>",
    "<risk 2: ...>"
  ],
  "stage_summaries": [
    {
      "stage": "<clarification | estimation | architecture | deep_dive | bottleneck | evaluation>",
      "stage_name": "<Human Readable Stage Name>",
      "duration_seconds": <estimated duration in seconds>,
      "turn_count": <turn count for stage>,
      "is_completed": true,
      "key_decisions": ["<decision 1>", "<decision 2>"],
      "interviewer_observations": "<commentary on communication, rigor, and speed>"
    }
  ],
  "improvement_tips": [
    {
      "pillar": "<one of the 5 scoring pillars>",
      "category": "<improvement | critical_gap | recommendation>",
      "title": "<concise title of the recommendation>",
      "detail": "<in-depth explanation of the technical concept and why it matters>",
      "action_items": [
        "<concrete practice task 1>",
        "<concrete practice task 2>"
      ],
      "resources": [
        {
          "title": "<book, paper, or article title>",
          "url": "<optional canonical URL or null>",
          "resource_type": "<book | paper | article | video>",
          "description": "<how this reading addresses the specific weakness>"
        }
      ]
    }
  ],
  "recommended_resources": [
    {
      "title": "<Canonical Learning Material Title>",
      "url": "<URL or null>",
      "resource_type": "<book | paper | article>",
      "description": "<Relevance explanation>"
    }
  ]
}
"""

# -----------------------------------------------------------------------------
# Context Helpers & Formatters
# -----------------------------------------------------------------------------

def format_stage_metrics_context(stage_metrics: list[dict[str, Any]] | None) -> str:
    """Format per-stage telemetry and performance metrics for the synthesis prompt."""
    if not stage_metrics:
        return "[Per-stage metrics telemetry not recorded]"

    lines: list[str] = ["### Stage Execution Telemetry:"]
    for metric in stage_metrics:
        stage = metric.get("stage", "unknown")
        stage_title = INTERVIEW_STAGE_TITLES.get(stage, stage.title())
        duration = metric.get("duration_seconds", 0)
        turns = metric.get("turn_count", 0)
        completed = metric.get("is_completed", True)
        lines.append(
            f"- Stage: {stage_title} | Duration: {duration}s | Turns: {turns} | Completed: {completed}"
        )
        decisions = metric.get("key_decisions", [])
        if decisions:
            lines.append("  Key Decisions:")
            for d in decisions:
                lines.append(f"    * {d}")
        obs = metric.get("interviewer_observations")
        if obs:
            lines.append(f"  Observations: {obs}")
    return "\n".join(lines)


def get_final_summary_prompt(
    context: PromptContext,
    stage_metrics: list[dict[str, Any]] | None = None,
    rubric_scores: dict[str, Any] | None = None,
) -> str:
    """Compose the master debrief and interview synthesis prompt.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        stage_metrics: Optional list of per-stage execution timing and telemetry records.
        rubric_scores: Optional dictionary of evaluated pillar scores and recommendations.

    Returns:
        Fully compiled user prompt string for generating the comprehensive debrief report.
    """
    metrics_str = format_stage_metrics_context(stage_metrics)
    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=60)
    artifacts_str = format_artifact_context(context.artifacts)

    rubric_scores_str = (
        json.dumps(rubric_scores, indent=2)
        if rubric_scores
        else "[Rubric scores to be synthesized directly from dialogue and artifacts]"
    )

    return f"""{FINAL_SUMMARY_SYSTEM_PROMPT}

================================================================================
INTERVIEW CONTEXT & METADATA
================================================================================
Problem Title: {context.problem_title}
Target Seniority Level: {context.candidate_level.upper()}
Total Conversational Turns: {len(context.dialogue_history)}

Problem Specification & Scale Targets:
{context.problem_description}
Scale Targets: {json.dumps(context.scale_targets, indent=2) if context.scale_targets else "N/A"}

================================================================================
EVALUATION PILLAR SCORES (PRE-COMPUTED OR REFERENCE)
================================================================================
{rubric_scores_str}

================================================================================
STAGE EXECUTION METRICS
================================================================================
{metrics_str}

================================================================================
WHITEBOARD ARTIFACTS, SCHEMAS & CALCULATIONS
================================================================================
{artifacts_str}

================================================================================
FULL INTERVIEW DIALOGUE TRANSCRIPT
================================================================================
{dialogue_str}

Synthesize the full session into the authoritative JSON debrief report:"""


def get_executive_summary_prompt(
    context: PromptContext,
    overall_score: float,
    hiring_recommendation: str,
) -> str:
    """Compose a focused prompt for generating an executive-level candidate summary.

    Args:
        context: Aggregated session state and problem metadata.
        overall_score: Evaluated numerical score on 1.0 to 5.0 scale.
        hiring_recommendation: Calibrated hiring recommendation string.

    Returns:
        Prompt string requesting executive summary narrative.
    """
    artifacts_str = format_artifact_context(context.artifacts)
    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=30)

    return f"""You are a Principal Engineering Director writing a concise hiring committee executive summary.
Candidate Target Level: {context.candidate_level.upper()}
Problem: {context.problem_title}
Overall Score: {overall_score:.2f} / 5.0
Hiring Recommendation: {hiring_recommendation.upper()}

CANDIDATE ARTIFACTS:
{artifacts_str}

RECENT DIALOGUE TRANSCRIPT:
{dialogue_str}

Write a 3-5 sentence executive summary detailing:
1. Candidate's core design intuition and architectural strengths.
2. How their performance compares against the expectations for {context.candidate_level.upper()}.
3. Critical blind spots or reasons for the recommendation.

Respond with ONLY the text of the executive summary:"""


def get_improvement_tips_prompt(
    context: PromptContext,
    growth_areas: list[str],
) -> str:
    """Compose a focused prompt for translating identified growth areas into actionable study plans.

    Args:
        context: Aggregated session state.
        growth_areas: List of observed candidate deficiencies and missed edge cases.

    Returns:
        Prompt string requesting structured improvement tips and learning resources JSON.
    """
    areas_str = "\n".join(f"- {area}" for area in growth_areas) if growth_areas else "- General system design depth"

    return f"""You are a Staff Technical Mentor generating a personalized system design improvement plan.
Candidate Target Level: {context.candidate_level.upper()}
Problem Evaluated: {context.problem_title}

OBSERVED GROWTH AREAS & DEFICIENCIES:
{areas_str}

STRICT JSON OUTPUT FORMAT:
Respond with a JSON array of ImprovementTip objects matching this schema:
[
  {{
    "pillar": "<requirements_and_clarification | system_architecture_and_data_flow | storage_data_model_and_scalability | resilience_fault_tolerance_and_monitoring | communication_and_trade_off_analysis>",
    "category": "improvement",
    "title": "<headline of the tip>",
    "detail": "<in-depth technical explanation>",
    "action_items": [
      "<specific drill or calculation to perform>",
      "<architecture trade-off to design>"
    ],
    "resources": [
      {{
        "title": "<book, paper, or article>",
        "url": null,
        "resource_type": "book",
        "description": "<why this reading helps>"
      }}
    ]
  }}
]

Generate the actionable improvement plan:"""

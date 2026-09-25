"""System Design Interview Simulator - Rubric Evaluation Prompt Templates.

Implements rubric-aligned scoring prompt templates, competency evaluation directives,
evidence extraction guidelines, and hiring recommendation calibration logic for the
5-pillar system design evaluation framework.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.core.constants import (
    SCORING_PILLAR_TITLES,
    ScoringPillar,
    SeniorityLevel,
)
from app.prompts.base import PromptContext, format_artifact_context, format_dialogue_history
from app.schemas.evaluation import HiringRecommendationEnum

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Rubric Scoring Core System Prompt
# -----------------------------------------------------------------------------

RUBRIC_EVALUATION_SYSTEM_PROMPT = """You are an objective, calibrated Senior Principal Systems Architect and Technical Interview Evaluator.
Your mandate is to perform a rigorous, evidence-based competency evaluation of a candidate's full system design interview session.
You will assess the candidate's performance across the 5 standard industry competency pillars:
1. Requirements & Scope Clarification (requirements_and_clarification)
2. High-Level Architecture & Data Flow (system_architecture_and_data_flow)
3. Storage, Data Models & Scalability (storage_data_model_and_scalability)
4. Resilience, Fault Tolerance & Recovery (resilience_fault_tolerance_and_monitoring)
5. Communication, Trade-offs & Justification (communication_and_trade_off_analysis)

SCORING PRINCIPLES:
1. EVIDENCE-BASED GROUNDING:
   - Every score MUST be anchored in concrete evidence from the interview dialogue or whiteboard artifacts.
   - Do NOT assume knowledge or competencies the candidate did not demonstrate.
   - Cite direct quotes or architectural decisions for both strengths and growth areas.

2. SENIORITY CALIBRATION:
   - Score relative to the candidate's target seniority level:
     * Junior (L3): Evaluated on basic modularity, grasping guidance, and fundamental data flow.
     * Mid-Level (L4): Expected to deliver a working end-to-end design, ballpark math, standard relational/caching schemas, and basic fault tolerance.
     * Senior (L5): Expected to drive the discussion independently, justify storage/sharding trade-offs, detail resilient protocols, and handle high-throughput bottlenecks.
     * Staff / Principal (L6+): Expected to proactively explore organizational blast radius, cross-datacenter CAP/PACELC constraints, multi-tier failure modes, financial/cloud cost economics, and clear architectural vision.

3. CALIBRATED NUMERICAL SCORING (1.0 to 5.0 scale):
   - 1.0 - 1.9: Unsatisfactory / Significantly below target bar.
   - 2.0 - 2.9: Developing / Marginal gaps for target bar; requires extensive hand-holding.
   - 3.0 - 3.7: Proficient / Solid performance meeting the target bar.
   - 3.8 - 4.5: Strong / Exceeds target bar with clean, defensive architecture.
   - 4.6 - 5.0: Exceptional / Deep mastery, role-model performance for this seniority level.

4. HIRING RECOMMENDATIONS:
   - "strong_hire": Overall score >= 4.5, with no pillar below 3.8.
   - "hire": Overall score >= 3.6, with no pillar below 3.0.
   - "lean_hire": Overall score between 3.0 and 3.59, with at most one pillar slightly below 3.0.
   - "lean_no_hire": Overall score between 2.4 and 2.99, or critical gaps in core pillars.
   - "strong_no_hire": Overall score < 2.4, or inability to establish a viable system topology.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding prose or markdown fences outside the JSON block.
Schema:
{
  "overall_score": <float between 1.0 and 5.0>,
  "recommended_level": "<junior | mid | senior | staff | principal>",
  "hiring_recommendation": "<strong_hire | hire | lean_hire | lean_no_hire | strong_no_hire>",
  "summary": "<executive debrief of 3-5 sentences summarizing strengths, technical depth, and level calibration>",
  "pillar_scores": {
    "requirements_and_clarification": {
      "pillar": "requirements_and_clarification",
      "pillar_title": "Requirements & Scope Clarification",
      "score": <float between 1.0 and 5.0>,
      "weight": 0.2,
      "strengths": ["<strength 1>", "<strength 2>"],
      "growth_areas": ["<growth area 1>", "<growth area 2>"],
      "evidence": ["<direct evidence or dialogue quote 1>", "<evidence 2>"]
    },
    "system_architecture_and_data_flow": {
      "pillar": "system_architecture_and_data_flow",
      "pillar_title": "High-Level Architecture & Data Flow",
      "score": <float between 1.0 and 5.0>,
      "weight": 0.2,
      "strengths": ["..."],
      "growth_areas": ["..."],
      "evidence": ["..."]
    },
    "storage_data_model_and_scalability": {
      "pillar": "storage_data_model_and_scalability",
      "pillar_title": "Storage, Data Models & Scalability",
      "score": <float between 1.0 and 5.0>,
      "weight": 0.2,
      "strengths": ["..."],
      "growth_areas": ["..."],
      "evidence": ["..."]
    },
    "resilience_fault_tolerance_and_monitoring": {
      "pillar": "resilience_fault_tolerance_and_monitoring",
      "pillar_title": "Resilience, Fault Tolerance & Recovery",
      "score": <float between 1.0 and 5.0>,
      "weight": 0.2,
      "strengths": ["..."],
      "growth_areas": ["..."],
      "evidence": ["..."]
    },
    "communication_and_trade_off_analysis": {
      "pillar": "communication_and_trade_off_analysis",
      "pillar_title": "Communication, Trade-offs & Justification",
      "score": <float between 1.0 and 5.0>,
      "weight": 0.2,
      "strengths": ["..."],
      "growth_areas": ["..."],
      "evidence": ["..."]
    }
  },
  "metadata_json": {
    "target_level": "<candidate target level>",
    "total_turns_analyzed": <integer>,
    "artifacts_considered": ["<list of artifact types>"]
  }
}
"""

# -----------------------------------------------------------------------------
# Rubric Context & Formatter Helpers
# -----------------------------------------------------------------------------

def format_rubric_criteria_context(rubric_data: dict[str, Any] | None) -> str:
    """Format evaluation rubric criteria descriptions and level expectations for prompt context."""
    if not rubric_data or "criteria" not in rubric_data:
        return "[Default 5-Pillar Rubric Standards Applied]"

    criteria_lines: list[str] = [f"Rubric: {rubric_data.get('name', 'Custom System Design Rubric')}"]
    if "description" in rubric_data:
        criteria_lines.append(f"Description: {rubric_data['description']}\n")

    for crit in rubric_data.get("criteria", []):
        pillar = crit.get("pillar", "unknown")
        title = crit.get("title", pillar)
        desc = crit.get("description", "")
        weight = crit.get("weight", 1.0)
        criteria_lines.append(f"### Pillar: {title} (ID: {pillar}, Weight: {weight})")
        criteria_lines.append(f"Expectation: {desc}")
        expectations = crit.get("level_expectations", {})
        if expectations:
            criteria_lines.append("Level Expectations:")
            for level, exp in expectations.items():
                criteria_lines.append(f"  * {level.upper()}: {exp}")
        criteria_lines.append("")

    return "\n".join(criteria_lines)


def get_rubric_evaluation_prompt(
    context: PromptContext,
    rubric_data: dict[str, Any] | None = None,
    stage_summaries: str = "",
) -> str:
    """Compose complete multi-pillar rubric scoring prompt for LLM evaluation.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        rubric_data: Optional dictionary containing rubric definition and criteria.
        stage_summaries: Optional textual summary of progress and decisions across stages.

    Returns:
        Fully compiled user prompt string ready for LLM scorecard generation.
    """
    rubric_str = format_rubric_criteria_context(rubric_data)
    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=50)
    artifacts_str = format_artifact_context(context.artifacts)

    problem_section = f"""PROBLEM STATEMENT:
Title: {context.problem_title}
Requirements & Constraints:
{context.problem_description}
Scale Targets: {json.dumps(context.scale_targets, indent=2) if context.scale_targets else "N/A"}
"""

    session_metrics = f"""INTERVIEW SESSION METRICS:
Target Seniority Level: {context.candidate_level.upper()}
Total Conversational Turns: {len(context.dialogue_history)}
Satisfied Stage Criteria: {', '.join(context.satisfied_criteria) if context.satisfied_criteria else 'None'}
"""

    return f"""{RUBRIC_EVALUATION_SYSTEM_PROMPT}

================================================================================
EVALUATION RUBRIC FRAMEWORK
================================================================================
{rubric_str}

================================================================================
DESIGN PROBLEM CONTEXT
================================================================================
{problem_section}

================================================================================
SESSION METRICS & STAGE SUMMARIES
================================================================================
{session_metrics}
{stage_summaries if stage_summaries.strip() else "[Stage-by-stage summaries not provided]"}

================================================================================
WHITEBOARD ARTIFACTS & CALCULATIONS
================================================================================
{artifacts_str}

================================================================================
FULL INTERVIEW DIALOGUE TRANSCRIPT
================================================================================
{dialogue_str}

Analyze the full interview transcript and artifacts against the rubric standards and candidate level ({context.candidate_level.upper()}).
Produce the calibrated JSON scorecard:"""


def get_single_pillar_evaluation_prompt(
    pillar: ScoringPillar,
    context: PromptContext,
    rubric_criterion: dict[str, Any] | None = None,
) -> str:
    """Compose a focused evaluation prompt targeting a single specific competency pillar.

    Args:
        pillar: The specific scoring pillar to evaluate.
        context: Aggregated session state, problem details, and dialogue history.
        rubric_criterion: Optional dictionary of criterion-specific expectations and rubrics.

    Returns:
        Fully compiled user prompt string for single-pillar assessment.
    """
    pillar_title = SCORING_PILLAR_TITLES.get(pillar, pillar.value)
    criterion_desc = ""
    level_expectations = ""

    if rubric_criterion:
        criterion_desc = rubric_criterion.get("description", "")
        exp_dict = rubric_criterion.get("level_expectations", {})
        if exp_dict:
            target_exp = exp_dict.get(context.candidate_level.lower(), "")
            if target_exp:
                level_expectations = f"Target Level Expectation ({context.candidate_level.upper()}): {target_exp}"

    dialogue_str = format_dialogue_history(context.dialogue_history, max_turns=30)
    artifacts_str = format_artifact_context(context.artifacts)

    return f"""You are an expert technical evaluator assessing a candidate on a SINGLE competency pillar:
Pillar: {pillar_title} (ID: {pillar.value})
Target Seniority Level: {context.candidate_level.upper()}

PILLAR DESCRIPTION:
{criterion_desc or "Evaluate candidate competence in this area based on industry standards."}

{level_expectations}

STRICT JSON OUTPUT FORMAT:
Respond with a JSON object matching this schema:
{{
  "pillar": "{pillar.value}",
  "pillar_title": "{pillar_title}",
  "score": <float between 1.0 and 5.0>,
  "weight": 0.2,
  "strengths": ["<concise strength 1>", "<strength 2>"],
  "growth_areas": ["<growth area 1>", "<growth area 2>"],
  "evidence": ["<dialogue citation or artifact evidence 1>", "<evidence 2>"]
}}

PROBLEM TITLE: {context.problem_title}

ARTIFACTS & CALCULATIONS:
{artifacts_str}

DIALOGUE TRANSCRIPT:
{dialogue_str}

Evaluate the candidate's performance strictly on {pillar_title}:"""

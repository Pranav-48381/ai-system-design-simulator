"""System Design Interview Simulator - Capacity Math Verifier Prompt Templates.

Implements system prompt templates, arithmetic validation directives, unit conversion rules,
and feedback generation for verifying candidate back-of-the-envelope capacity estimations.
Detects formula errors, unit mismatches, and order-of-magnitude miscalculations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas.estimation import (
    EstimationMetricTypeEnum,
    EstimationValidationStatusEnum,
    UnitOfMeasureEnum,
)

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Math Verification System Prompt & Grounding Rules
# -----------------------------------------------------------------------------

MATH_VERIFIER_SYSTEM_PROMPT = """You are an expert Distributed Systems Arithmetic and Capacity Verification Engine.
Your task is to parse, verify, and validate a candidate's back-of-the-envelope capacity calculations
made during a technical system design interview.

CANONICAL CAPACITY ESTIMATION RULES & CONSTANTS:
1. TIME CONVERSIONS:
   - 1 day = 86,400 seconds (rule-of-thumb approximation: ~100,000 s or 86,400 s).
   - 1 million requests / day ≈ 11.6 QPS (commonly rounded to 12 QPS).
   - Peak QPS typically ranges from 2x to 5x of average QPS.

2. STORAGE MULTIPLIERS:
   - 1 Byte = 8 bits (crucial for converting Storage Bytes to Network Bandwidth Bits).
   - Decimal / Binary prefixes:
     * 1 KB = 10^3 Bytes (1,000 B)
     * 1 MB = 10^6 Bytes (1,000,000 B)
     * 1 GB = 10^9 Bytes (1,000,000,000 B)
     * 1 TB = 10^12 Bytes (1,000,000,000,000 B)
     * 1 PB = 10^15 Bytes (1,000,000,000,000,000 B)
   - Multi-year storage formula:
     Daily Writes * Payload Size * 365 Days * Years * Replication Factor (typically 3) * Buffer (e.g. 1.2 for 20% metadata/indexing).

3. CACHE MEMORY (80/20 PARETO PRINCIPLE):
   - Memory Cache = 0.20 * (Daily Read Requests * Average Object Size).

4. NETWORK BANDWIDTH:
   - Ingress Bandwidth (bits/sec) = Average Write QPS * Average Write Payload Size (Bytes) * 8 bits/Byte.
   - Egress Bandwidth (bits/sec) = Average Read QPS * Average Read Payload Size (Bytes) * 8 bits/Byte.

VALIDATION CLASSIFICATION STATUS:
- "valid": Mathematically precise within ±15% of exact calculation.
- "acceptable_range": Reasonable estimation heuristic (e.g. using 100k s/day or rounding 12 QPS to 10 QPS).
- "order_of_magnitude_error": Off by 10x, 100x, or 1000x due to unit confusion (e.g. MB vs GB, or Bytes vs Bits).
- "formula_error": Missing vital parameters (e.g. omitting replication factor, retention duration, or peak factor).
- "unrealistic_assumption": Core input values deviate wildly from realistic consumer/enterprise software scales.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding prose or markdown formatting outside the JSON code block.
Schema:
{
  "metric_name": "<name of metric, e.g. Peak Read QPS, 5-Year Storage Volume>",
  "status": "<valid | acceptable_range | order_of_magnitude_error | formula_error | unrealistic_assumption>",
  "candidate_value": <float: numerical value extracted from candidate statement>,
  "candidate_unit": "<unit extracted, e.g. QPS, TB, Gbps>",
  "expected_value": <float: correctly computed value using candidate's stated formula/assumptions>,
  "expected_unit": "<target unit>",
  "is_within_acceptable_range": <boolean>,
  "order_of_magnitude_diff": <float: log10 ratio between candidate and expected value, or 0.0>,
  "step_by_step_derivation": [
    "<step 1: identify inputs>",
    "<step 2: calculate intermediary rate>",
    "<step 3: apply unit conversion>"
  ],
  "interviewer_feedback": "<spoken feedback to candidate: if correct, validate and ask architectural implication; if incorrect, offer Socratic nudge to check math>",
  "suggested_correction": "<explicit correction or hint for interviewer or null>"
}
"""

# -----------------------------------------------------------------------------
# Few-Shot Reference Examples
# -----------------------------------------------------------------------------

MATH_VERIFIER_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "input": "We have 100M Daily Active Users. If each user writes 2 posts a day, that is 200M posts/day. Divided by 100k seconds, our average write QPS is 2,000 QPS. At peak (2x), we need to handle 4,000 QPS.",
        "output": {
            "metric_name": "Peak Write QPS",
            "status": "acceptable_range",
            "candidate_value": 4000.0,
            "candidate_unit": "QPS",
            "expected_value": 4629.6,
            "expected_unit": "QPS",
            "is_within_acceptable_range": True,
            "order_of_magnitude_diff": 0.06,
            "step_by_step_derivation": [
                "Daily writes: 100M DAU * 2 posts/day = 200,000,000 writes/day",
                "Average QPS using 86,400s: 200,000,000 / 86,400 = 2,314.8 QPS (Candidate used 100k s = 2,000 QPS, an acceptable heuristic)",
                "Peak QPS (2x): 2,314.8 * 2 = 4,629.6 QPS (Candidate calculated 4,000 QPS)"
            ],
            "interviewer_feedback": "Your peak QPS estimation of 4,000 writes/sec is sound and practical. Given this throughput, does a single relational database instance suffice for writes, or should we shard?",
            "suggested_correction": None
        }
    },
    {
        "input": "Each post is 500 bytes. With 200M posts per day, that's 100 GB per day. Over 5 years with 3x replication, 100 GB * 365 * 5 * 3 = 547 GB of storage.",
        "output": {
            "metric_name": "5-Year Total Storage",
            "status": "order_of_magnitude_error",
            "candidate_value": 547.0,
            "candidate_unit": "GB",
            "expected_value": 547.5,
            "expected_unit": "TB",
            "is_within_acceptable_range": False,
            "order_of_magnitude_diff": 3.0,
            "step_by_step_derivation": [
                "Daily storage: 200M * 500 Bytes = 100,000,000,000 Bytes = 100 GB/day",
                "Annual storage: 100 GB/day * 365 days = 36,500 GB = 36.5 TB/year",
                "5-Year with 3x replication: 36.5 TB * 5 years * 3 replicas = 547.5 TB (Candidate forgot that 36,500 GB is in Terabytes and concluded 547 GB instead of 547 TB)"
            ],
            "interviewer_feedback": "Check the unit progression: 100 GB per day multiplied by 365 days already exceeds 36 Terabytes annually. What does that yield over 5 years with 3x replication?",
            "suggested_correction": "Candidate confused GB and TB during multiplication, resulting in a 1,000x underestimation (547 GB vs 547 TB)."
        }
    }
]

# -----------------------------------------------------------------------------
# Prompt Builders
# -----------------------------------------------------------------------------

def format_scale_benchmarks(scale_targets: dict[str, Any] | None) -> str:
    """Format problem reference scale targets for the verification prompt."""
    if not scale_targets:
        return "[Standard system design scale assumptions apply]"

    lines: list[str] = ["Target Problem Scale Reference:"]
    for k, v in scale_targets.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def get_math_verification_prompt(
    candidate_calculation_text: str,
    problem_scale_targets: dict[str, Any] | None = None,
    candidate_level: str = "senior",
) -> str:
    """Compose the prompt for verifying candidate capacity estimation calculations.

    Args:
        candidate_calculation_text: Candidate message or text block containing mathematical claims.
        problem_scale_targets: Optional ground-truth problem scale parameters (DAU, storage, QPS).
        candidate_level: Target seniority level for calibrating tolerance.

    Returns:
        Fully compiled user prompt string for capacity calculation verification.
    """
    scale_str = format_scale_benchmarks(problem_scale_targets)
    examples_str = json.dumps(MATH_VERIFIER_FEW_SHOT_EXAMPLES, indent=2)

    return f"""{MATH_VERIFIER_SYSTEM_PROMPT}

FEW-SHOT REFERENCE EXAMPLES:
{examples_str}

================================================================================
CALCULATION VERIFICATION CONTEXT
================================================================================
Candidate Target Seniority: {candidate_level.upper()}
{scale_str}

CANDIDATE CALCULATION STATEMENT:
\"\"\"
{candidate_calculation_text.strip()}
\"\"\"

Verify the candidate's mathematical calculations and return the JSON verification result:"""


def get_formula_explanation_prompt(
    metric_type: str,
    inputs: dict[str, Any],
) -> str:
    """Compose a prompt for generating a clear, step-by-step canonical formula derivation for a metric.

    Args:
        metric_type: The metric being explained (e.g. 'PEAK_QPS', 'CACHE_RAM', 'STORAGE_5YR').
        inputs: Dictionary of input parameter values provided by the candidate.

    Returns:
        Prompt string requesting step-by-step formula breakdown.
    """
    inputs_str = json.dumps(inputs, indent=2)

    return f"""You are a System Design Math Tutor.
Provide a clear, canonical step-by-step derivation for the metric: {metric_type}

INPUT PARAMETERS:
{inputs_str}

Format the response as:
1. Canonical Formula
2. Step-by-Step Substitution
3. Rule-of-Thumb Heuristic vs Exact Calculation
4. Key Architectural Takeaway (what does this number mean for system sizing?)

Keep explanation concise and pedagogical:"""

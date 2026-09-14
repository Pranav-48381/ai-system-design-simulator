"""System Design Interview Simulator - Capacity Estimation Schemas.

Defines Pydantic schemas for back-of-the-envelope calculations, scale assumptions,
metric calculations (QPS, storage, bandwidth, memory), and validation evaluations.
"""

from enum import StrEnum
from datetime import datetime, timezone
import uuid
from pydantic import Field

from app.schemas import BaseSchema


class EstimationMetricTypeEnum(StrEnum):
    """Architectural metrics targeted in back-of-the-envelope calculations."""

    DAU = "dau"
    MAU = "mau"
    QPS_READ = "qps_read"
    QPS_WRITE = "qps_write"
    PEAK_QPS = "peak_qps"
    STORAGE_DAILY = "storage_daily"
    STORAGE_TOTAL = "storage_total"
    BANDWIDTH_IN = "bandwidth_in"
    BANDWIDTH_OUT = "bandwidth_out"
    MEMORY_CACHE = "memory_cache"
    CONNECTION_CONCURRENCY = "connection_concurrency"
    CUSTOM = "custom"


class UnitOfMeasureEnum(StrEnum):
    """Standardized measurement units for capacity estimations."""

    REQUESTS_PER_SECOND = "req/s"
    QUERIES_PER_SECOND = "qps"
    BYTES = "B"
    KILOBYTES = "KB"
    MEGABYTES = "MB"
    GIGABYTES = "GB"
    TERABYTES = "TB"
    PETABYTES = "PB"
    MEGABITS_PER_SECOND = "Mbps"
    GIGABITS_PER_SECOND = "Gbps"
    COUNT = "count"
    PERCENTAGE = "%"


class EstimationValidationStatusEnum(StrEnum):
    """Validation classification for candidate calculations against reference blueprints."""

    VALID = "valid"
    ACCEPTABLE_RANGE = "acceptable_range"
    ORDER_OF_MAGNITUDE_ERROR = "order_of_magnitude_error"
    FORMULA_ERROR = "formula_error"
    UNREALISTIC_ASSUMPTION = "unrealistic_assumption"


class EstimationAssumptionSchema(BaseSchema):
    """Underlying assumption provided or inferred by the candidate."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the assumption.",
        examples=["dau-base"],
    )
    name: str = Field(
        ...,
        description="Name of the assumed parameter or traffic profile.",
        examples=["Daily Active Users (DAU)"],
    )
    assumed_value: float = Field(
        ...,
        ge=0.0,
        description="Assumed numerical quantity.",
        examples=[500000000.0],
    )
    unit: str = Field(
        ...,
        description="Measurement unit for the assumption.",
        examples=["count", "req/day"],
    )
    rationale: str | None = Field(
        default=None,
        description="Candidate reasoning or justification for the assumed value.",
        examples=["Assuming a globally scaled consumer social messaging platform."],
    )


class EstimationCalculationSchema(BaseSchema):
    """Derived calculation produced by candidate during capacity estimation."""

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4())[:8],
        description="Unique identifier for the calculation.",
        examples=["calc-peak-qps"],
    )
    metric_type: EstimationMetricTypeEnum = Field(
        ...,
        description="Classification of metric being computed.",
        examples=[EstimationMetricTypeEnum.PEAK_QPS],
    )
    metric_name: str = Field(
        ...,
        description="Human-readable title of the calculated metric.",
        examples=["Peak Read QPS"],
    )
    formula: str = Field(
        ...,
        description="Mathematical equation or breakdown used for estimation.",
        examples=["(DAU * 100 reads/day) / 86400 * 2 (peak factor)"],
    )
    calculated_value: float = Field(
        ...,
        ge=0.0,
        description="Resulting calculated value from the formula.",
        examples=[115740.74],
    )
    unit: str = Field(
        ...,
        description="Target unit of measure.",
        examples=["req/s", "TB/year"],
    )
    assumptions_used: list[str] = Field(
        default_factory=list,
        description="List of assumption IDs or names factored into the calculation.",
        examples=[["dau-base", "read-write-ratio"]],
    )
    notes: str | None = Field(
        default=None,
        description="Optional candidate notes or engineering trade-offs considered.",
    )


class EstimationValidationResultSchema(BaseSchema):
    """Automated or interviewer evaluation of candidate capacity estimations."""

    calculation_id: str | None = Field(
        default=None,
        description="Reference calculation ID evaluated.",
    )
    metric_name: str = Field(
        ...,
        description="Name of the metric evaluated.",
        examples=["Peak Read QPS"],
    )
    status: EstimationValidationStatusEnum = Field(
        ...,
        description="Evaluation judgment status.",
        examples=[EstimationValidationStatusEnum.ACCEPTABLE_RANGE],
    )
    candidate_value: float = Field(
        ...,
        description="Value computed by candidate.",
    )
    reference_value: float | None = Field(
        default=None,
        description="Benchmark reference value from problem blueprint.",
    )
    acceptable_min: float | None = Field(
        default=None,
        description="Lower bound of acceptable engineering estimation range.",
    )
    acceptable_max: float | None = Field(
        default=None,
        description="Upper bound of acceptable engineering estimation range.",
    )
    is_within_acceptable_range: bool = Field(
        ...,
        description="True if calculation falls within realistic orders of magnitude.",
    )
    order_of_magnitude_diff: float | None = Field(
        default=None,
        description="Log10 difference between candidate estimate and benchmark.",
    )
    interviewer_feedback: str = Field(
        ...,
        description="Interviewer critique, Socratic question, or confirmation.",
        examples=["Your QPS math is sound. Don't forget caching impact on storage bandwidth."],
    )
    suggested_correction: str | None = Field(
        default=None,
        description="Specific adjustment hint if calculation went astray.",
    )


class EstimationStageSummarySchema(BaseSchema):
    """Comprehensive snapshot of the capacity estimation stage."""

    session_id: uuid.UUID = Field(
        ...,
        description="Associated interview session UUID.",
    )
    assumptions: list[EstimationAssumptionSchema] = Field(
        default_factory=list,
        description="Set of baseline assumptions documented by candidate.",
    )
    calculations: list[EstimationCalculationSchema] = Field(
        default_factory=list,
        description="Key capacity calculations computed.",
    )
    validation_results: list[EstimationValidationResultSchema] = Field(
        default_factory=list,
        description="Evaluations generated for the calculations.",
    )
    overall_accuracy_score: float = Field(
        default=5.0,
        ge=1.0,
        le=5.0,
        description="Aggregated score (1-5) representing estimation rigor.",
    )
    is_completed: bool = Field(
        default=False,
        description="Flag indicating candidate has finalized capacity estimations.",
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Timestamp when estimation stage was marked complete.",
    )

"""System Design Interview Simulator - Problem Schemas and DTOs.

Defines Pydantic models for system design interview problems, scale assumptions,
architectural requirements, and catalog browsing filters.
"""

import uuid
from datetime import datetime
from typing import Any
from pydantic import Field

from app.core.constants import ProblemDifficulty
from app.schemas import BaseSchema


class TagRead(BaseSchema):
    """Architectural classification tag DTO."""

    id: uuid.UUID = Field(description="Tag unique UUID.")
    name: str = Field(description="Tag label name.", examples=["Distributed Caching"])
    slug: str = Field(description="URL-friendly tag slug identifier.", examples=["distributed-caching"])
    description: str | None = Field(default=None, description="Detailed concept description.")


class ProblemBase(BaseSchema):
    """Core attributes common across problem inputs and outputs."""

    slug: str = Field(
        ...,
        min_length=3,
        max_length=128,
        description="Unique URL-friendly slug identifier for the problem.",
        examples=["url-shortener-tinyurl"],
    )
    title: str = Field(
        ...,
        min_length=3,
        max_length=255,
        description="Concise system design interview problem title.",
        examples=["Design a Scalable URL Shortener (TinyURL)"],
    )
    summary: str = Field(
        ...,
        min_length=10,
        description="High-level single paragraph overview of system scope.",
    )
    description: str = Field(
        ...,
        min_length=20,
        description="Full problem statement provided to the candidate at session start.",
    )
    difficulty: ProblemDifficulty = Field(
        default=ProblemDifficulty.MEDIUM,
        description="Target challenge difficulty tier.",
        examples=[ProblemDifficulty.MEDIUM],
    )
    functional_requirements: list[str] = Field(
        default_factory=list,
        description="List of expected core functional capabilities.",
        examples=[["Generate unique shortened URL", "Redirect short URL to original destination"]],
    )
    non_functional_requirements: list[str] = Field(
        default_factory=list,
        description="System qualities (availability, latency, consistency, durability).",
        examples=[["Low latency redirection (< 20ms)", "High availability (99.99%)"]],
    )
    scale_targets: dict[str, Any] = Field(
        default_factory=dict,
        description="Quantitative operational constraints (QPS, DAU, storage, retention).",
        examples=[{"daily_active_users": 100000000, "read_write_ratio": "100:1"}],
    )
    key_challenges: list[str] = Field(
        default_factory=list,
        description="Critical failure modes and deep dive focus topics.",
        examples=[["Hash collision resolution", "Cache stampede prevention"]],
    )


class ProblemCreate(ProblemBase):
    """Schema for authoring a new system design interview challenge."""

    reference_solution: dict[str, Any] | None = Field(
        default=None,
        description="Staff-level reference architecture blueprint and trade-off rubric notes.",
    )
    tag_slugs: list[str] = Field(
        default_factory=list,
        description="List of existing tag slug identifiers to associate.",
    )


class ProblemUpdate(BaseSchema):
    """Schema for modifying existing problem definitions."""

    title: str | None = Field(default=None, min_length=3, max_length=255)
    summary: str | None = Field(default=None, min_length=10)
    description: str | None = Field(default=None, min_length=20)
    difficulty: ProblemDifficulty | None = None
    functional_requirements: list[str] | None = None
    non_functional_requirements: list[str] | None = None
    scale_targets: dict[str, Any] | None = None
    key_challenges: list[str] | None = None
    reference_solution: dict[str, Any] | None = None
    is_active: bool | None = None
    tag_slugs: list[str] | None = None


class ProblemSummary(BaseSchema):
    """Lightweight problem metadata for catalog search and listing views."""

    id: uuid.UUID = Field(description="Unique problem identifier.")
    slug: str = Field(description="URL-safe slug.")
    title: str = Field(description="Problem title.")
    summary: str = Field(description="Brief summary overview.")
    difficulty: ProblemDifficulty = Field(description="Difficulty tier.")
    tags: list[TagRead] = Field(default_factory=list, description="Categorization tags.")
    is_active: bool = Field(description="Active flag.")
    created_at: datetime = Field(description="Creation timestamp.")


class ProblemRead(ProblemBase):
    """Full problem representation exposed to candidates during active interviews."""

    id: uuid.UUID = Field(description="Unique problem identifier.")
    is_active: bool = Field(description="Whether problem is enabled for new sessions.")
    tags: list[TagRead] = Field(default_factory=list, description="Associated system design tags.")
    created_at: datetime = Field(description="Creation timestamp.")
    updated_at: datetime = Field(description="Last modification timestamp.")


class ProblemDetail(ProblemRead):
    """Administrative problem view including internal reference solutions and rubrics."""

    reference_solution: dict[str, Any] | None = Field(
        default=None,
        description="Complete reference architectural solution and calculation steps.",
    )


class ProblemFilterParams(BaseSchema):
    """Filtering options for searching and querying the problem catalog."""

    difficulty: ProblemDifficulty | None = Field(default=None, description="Filter by difficulty tier.")
    tag: str | None = Field(default=None, description="Filter by tag slug.")
    search: str | None = Field(default=None, description="Free-text search query in title and summary.")

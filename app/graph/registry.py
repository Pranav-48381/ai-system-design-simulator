"""System Design Interview Simulator - LangGraph Runner Registry.

Provides a versioned registry of compiled StateGraph runners, execution factories,
and dynamic model switching profiles. Enables tier-based model allocation across
interview stages (e.g., low-latency chat vs deep reasoning evaluation), automated
provider fallback chains, and extensible multi-version graph topology selection.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
import logging
from typing import Any

from app.core.constants import InterviewStage
from app.graph.checkpointer import BaseCheckpointerProvider
from app.graph.config import GraphConfig

logger = logging.getLogger(__name__)


class ModelTier(StrEnum):
    """Categorization of LLM capabilities and cost/latency profiles."""

    FAST = "fast"              # Low latency, high throughput (e.g., gpt-4o-mini, gemini-1.5-flash)
    STANDARD = "standard"      # General conversation & synthesis (e.g., gpt-4o, claude-3-5-haiku)
    REASONING = "reasoning"    # Complex architecture & trade-off critique (e.g., claude-3-5-sonnet, gemini-1.5-pro)
    EVALUATOR = "evaluator"    # Exhaustive 5-pillar rubric scoring & scorecard generation


class ModelProvider(StrEnum):
    """Supported upstream LLM providers and backends."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    MOCK = "mock"


@dataclass(frozen=True)
class ModelProfile:
    """Detailed capability, hyperparameter, and cost configuration for a model."""

    model_id: str
    provider: ModelProvider
    tier: ModelTier
    context_window: int = 128000
    default_temperature: float = 0.2
    max_tokens: int = 2048
    supports_streaming: bool = True
    supports_tools: bool = True
    cost_per_1m_input_tokens: float = 0.0
    cost_per_1m_output_tokens: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider.value,
            "tier": self.tier.value,
            "context_window": self.context_window,
            "default_temperature": self.default_temperature,
            "max_tokens": self.max_tokens,
            "supports_streaming": self.supports_streaming,
            "supports_tools": self.supports_tools,
            "cost_per_1m_input_tokens": self.cost_per_1m_input_tokens,
            "cost_per_1m_output_tokens": self.cost_per_1m_output_tokens,
        }


# Standard pre-registered model catalog
DEFAULT_MODEL_CATALOG: dict[str, ModelProfile] = {
    # Fast Tier
    "gpt-4o-mini": ModelProfile(
        model_id="gpt-4o-mini",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.FAST,
        context_window=128000,
        default_temperature=0.3,
        max_tokens=2048,
        cost_per_1m_input_tokens=0.15,
        cost_per_1m_output_tokens=0.60,
    ),
    "gemini-1.5-flash": ModelProfile(
        model_id="gemini-1.5-flash",
        provider=ModelProvider.GEMINI,
        tier=ModelTier.FAST,
        context_window=1000000,
        default_temperature=0.3,
        max_tokens=2048,
        cost_per_1m_input_tokens=0.075,
        cost_per_1m_output_tokens=0.30,
    ),
    "claude-3-5-haiku": ModelProfile(
        model_id="claude-3-5-haiku",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.FAST,
        context_window=200000,
        default_temperature=0.3,
        max_tokens=2048,
        cost_per_1m_input_tokens=0.80,
        cost_per_1m_output_tokens=4.00,
    ),
    # Standard & Reasoning Tier
    "gpt-4o": ModelProfile(
        model_id="gpt-4o",
        provider=ModelProvider.OPENAI,
        tier=ModelTier.STANDARD,
        context_window=128000,
        default_temperature=0.2,
        max_tokens=4096,
        cost_per_1m_input_tokens=2.50,
        cost_per_1m_output_tokens=10.00,
    ),
    "claude-3-5-sonnet": ModelProfile(
        model_id="claude-3-5-sonnet",
        provider=ModelProvider.ANTHROPIC,
        tier=ModelTier.REASONING,
        context_window=200000,
        default_temperature=0.15,
        max_tokens=4096,
        cost_per_1m_input_tokens=3.00,
        cost_per_1m_output_tokens=15.00,
    ),
    "gemini-1.5-pro": ModelProfile(
        model_id="gemini-1.5-pro",
        provider=ModelProvider.GEMINI,
        tier=ModelTier.REASONING,
        context_window=2000000,
        default_temperature=0.2,
        max_tokens=4096,
        cost_per_1m_input_tokens=3.50,
        cost_per_1m_output_tokens=10.50,
    ),
    # Mock / Testing Tier
    "mock-interviewer": ModelProfile(
        model_id="mock-interviewer",
        provider=ModelProvider.MOCK,
        tier=ModelTier.FAST,
        context_window=32000,
        default_temperature=0.0,
        max_tokens=1024,
        cost_per_1m_input_tokens=0.0,
        cost_per_1m_output_tokens=0.0,
    ),
}

# Stage to default recommended model tier mapping
DEFAULT_STAGE_TIER_MAPPING: dict[InterviewStage, ModelTier] = {
    InterviewStage.CLARIFICATION: ModelTier.FAST,
    InterviewStage.ESTIMATION: ModelTier.STANDARD,
    InterviewStage.ARCHITECTURE: ModelTier.REASONING,
    InterviewStage.DEEP_DIVE: ModelTier.REASONING,
    InterviewStage.BOTTLENECK: ModelTier.REASONING,
    InterviewStage.EVALUATION: ModelTier.EVALUATOR,
}

# Fallback sequence when primary provider hits rate limits or downtime
DEFAULT_FALLBACK_CHAINS: dict[str, list[str]] = {
    "claude-3-5-sonnet": ["gpt-4o", "gemini-1.5-pro"],
    "gpt-4o": ["claude-3-5-sonnet", "gemini-1.5-pro"],
    "gemini-1.5-pro": ["gpt-4o", "claude-3-5-sonnet"],
    "gpt-4o-mini": ["gemini-1.5-flash", "claude-3-5-haiku"],
    "gemini-1.5-flash": ["gpt-4o-mini", "claude-3-5-haiku"],
    "claude-3-5-haiku": ["gpt-4o-mini", "gemini-1.5-flash"],
}

# Runner factory signature: takes GraphConfig and optional Checkpointer, returns compiled graph runner
GraphRunnerFactory = Callable[[GraphConfig, BaseCheckpointerProvider | None], Any]


class GraphRunnerRegistry:
    """Central registry for versioned graph runners, model profiles, and dynamic routing."""

    def __init__(self) -> None:
        self._runners: dict[str, GraphRunnerFactory] = {}
        self._default_version: str = "v1"
        self._models: dict[str, ModelProfile] = dict(DEFAULT_MODEL_CATALOG)
        self._fallbacks: dict[str, list[str]] = dict(DEFAULT_FALLBACK_CHAINS)
        self._stage_tiers: dict[InterviewStage, ModelTier] = dict(DEFAULT_STAGE_TIER_MAPPING)

    # -------------------------------------------------------------------------
    # Graph Runner Registration & Retrieval
    # -------------------------------------------------------------------------

    def register_runner(
        self,
        version: str,
        factory: GraphRunnerFactory,
        is_default: bool = False,
    ) -> None:
        """Register a versioned graph runner factory.

        Args:
            version: Unique version key (e.g. 'v1', 'v1_fast', 'v2_adaptive').
            factory: Callable producing a compiled LangGraph Runnable.
            is_default: If True, designates this version as the default runner.
        """
        cleaned_version = version.strip().lower()
        self._runners[cleaned_version] = factory
        if is_default or len(self._runners) == 1:
            self._default_version = cleaned_version
        logger.info("Registered graph runner version '%s' (default=%s)", cleaned_version, is_default)

    def get_runner_factory(self, version: str | None = None) -> GraphRunnerFactory:
        """Retrieve the graph runner factory for the requested or default version."""
        ver = (version or self._default_version).strip().lower()
        if ver not in self._runners:
            if self._default_version in self._runners:
                logger.warning(
                    "Graph runner version '%s' not found. Falling back to default '%s'",
                    ver,
                    self._default_version,
                )
                return self._runners[self._default_version]
            raise KeyError(
                f"No graph runner registered for version '{ver}' and no default runner configured."
            )
        return self._runners[ver]

    def list_runner_versions(self) -> list[str]:
        """List all registered graph runner versions."""
        return sorted(self._runners.keys())

    # -------------------------------------------------------------------------
    # Model Profile Management & Dynamic Model Switching
    # -------------------------------------------------------------------------

    def register_model_profile(self, profile: ModelProfile) -> None:
        """Register or update an LLM model profile."""
        self._models[profile.model_id] = profile
        logger.debug("Registered model profile '%s' in tier '%s'", profile.model_id, profile.tier)

    def get_model_profile(self, model_id: str) -> ModelProfile:
        """Retrieve model profile by model identifier string."""
        if model_id not in self._models:
            # Fallback to standard gpt-4o or first registered model
            logger.warning("Model '%s' not recognized in registry. Using 'gpt-4o' fallback.", model_id)
            return self._models.get("gpt-4o") or next(iter(self._models.values()))
        return self._models[model_id]

    def resolve_model_for_stage(
        self,
        stage: InterviewStage,
        preferred_model: str | None = None,
        provider_preference: ModelProvider | None = None,
    ) -> ModelProfile:
        """Dynamically resolve the most appropriate model profile for a given interview stage.

        If a preferred_model is explicitly supplied and matches stage tier appropriateness,
        it is honored. Otherwise, resolves the ideal profile based on calibrated stage tier
        (e.g., fast models for initial clarification vs deep reasoning models for architecture).

        Args:
            stage: Current interview stage.
            preferred_model: Candidate or system requested model name.
            provider_preference: Optional constraint to prioritize a specific LLM vendor.

        Returns:
            Resolved ModelProfile ready for invocation.
        """
        # 1. Direct match if preferred_model is registered
        if preferred_model and preferred_model in self._models:
            return self._models[preferred_model]

        # 2. Determine target tier for this stage
        target_tier = self._stage_tiers.get(stage, ModelTier.STANDARD)

        # 3. Find matching model in target tier (honoring provider_preference if given)
        for profile in self._models.values():
            if profile.tier == target_tier:
                if provider_preference is None or profile.provider == provider_preference:
                    return profile

        # 4. Secondary fallback: check STANDARD tier
        for profile in self._models.values():
            if profile.tier == ModelTier.STANDARD:
                if provider_preference is None or profile.provider == provider_preference:
                    return profile

        # 5. Ultimate fallback
        return self.get_model_profile("gpt-4o")

    def get_fallback_model(self, current_model_id: str) -> ModelProfile | None:
        """Determine next fallback model if current model encounters errors or rate limits.

        Args:
            current_model_id: Model that just failed.

        Returns:
            Alternative ModelProfile or None if no fallbacks exist.
        """
        fallbacks = self._fallbacks.get(current_model_id, [])
        for fb_id in fallbacks:
            if fb_id in self._models:
                logger.info("Failing over from '%s' to fallback model '%s'", current_model_id, fb_id)
                return self._models[fb_id]
        return None

    def configure_fallback_chain(self, primary_model_id: str, fallback_ids: list[str]) -> None:
        """Configure custom fallback chain for a primary model."""
        self._fallbacks[primary_model_id] = list(fallback_ids)

    def list_model_profiles(self) -> list[ModelProfile]:
        """Return list of all registered model profiles."""
        return list(self._models.values())


# Global singleton registry instance
_GLOBAL_REGISTRY = GraphRunnerRegistry()


def get_graph_registry() -> GraphRunnerRegistry:
    """Retrieve the global singleton GraphRunnerRegistry."""
    return _GLOBAL_REGISTRY

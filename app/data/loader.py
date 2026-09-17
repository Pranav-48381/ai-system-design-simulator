"""System Design Interview Simulator - Problem and Data Loader.

Provides centralized loaders for system design problem specifications,
evaluation rubrics, and interviewer personas with comprehensive Pydantic v2 validation.
"""

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import EntityNotFoundError, ValidationError
from app.core.logging import get_logger
from app.data import (
    PERSONAS_DIR,
    PROBLEMS_DIR,
    RUBRICS_DIR,
    list_problem_files,
)
from app.schemas.persona import InterviewerPersonaConfigSchema
from app.schemas.problem import ProblemCreate
from app.schemas.rubric import RubricCreate

logger = get_logger(__name__)


class DataLoader:
    """Orchestrates filesystem discovery, parsing, and Pydantic validation of seed data."""

    def __init__(
        self,
        problems_dir: Path = PROBLEMS_DIR,
        rubrics_dir: Path = RUBRICS_DIR,
        personas_dir: Path = PERSONAS_DIR,
    ) -> None:
        self.problems_dir = problems_dir
        self.rubrics_dir = rubrics_dir
        self.personas_dir = personas_dir
        self._problem_cache: dict[str, ProblemCreate] = {}
        self._rubric_cache: dict[str, RubricCreate] = {}
        self._persona_cache: dict[str, InterviewerPersonaConfigSchema] = {}

    def load_problem_file(self, file_path: Path) -> ProblemCreate:
        """Parse and validate a single problem definition JSON file.

        Args:
            file_path: Absolute or relative filesystem path to the problem JSON file.

        Returns:
            Validated ProblemCreate schema instance.

        Raises:
            EntityNotFoundError: If the file does not exist.
            ValidationError: If the JSON is malformed or schema validation fails.
        """
        if not file_path.is_file():
            logger.error("Problem file does not exist: %s", file_path)
            raise EntityNotFoundError("ProblemFile", str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in problem file '%s': %s", file_path.name, exc)
            raise ValidationError(
                message=f"Problem file '{file_path.name}' contains invalid JSON syntax.",
                details={"file": str(file_path), "error": str(exc)},
            ) from exc

        try:
            problem = ProblemCreate.model_validate(data)
        except PydanticValidationError as exc:
            logger.error("Schema validation failed for problem '%s': %s", file_path.name, exc)
            raise ValidationError(
                message=f"Problem file '{file_path.name}' failed schema validation.",
                details={"file": str(file_path), "errors": exc.errors()},
            ) from exc

        self._problem_cache[problem.slug] = problem
        return problem

    def load_problem_by_slug(self, slug: str) -> ProblemCreate:
        """Find and validate a problem specification by its URL-friendly slug.

        Args:
            slug: Unique slug identifier for the problem (e.g., 'url-shortener-tinyurl').

        Returns:
            Validated ProblemCreate schema instance.

        Raises:
            EntityNotFoundError: If no matching problem specification is found.
        """
        if slug in self._problem_cache:
            return self._problem_cache[slug]

        # Scan problems directory for matching slug
        for path in self.list_problem_files():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("slug") == slug:
                    return self.load_problem_file(path)
            except (json.JSONDecodeError, OSError):
                continue

        raise EntityNotFoundError("SystemDesignProblem", slug)

    def list_problem_files(self) -> list[Path]:
        """Return all problem JSON files located in the configured directory."""
        if not self.problems_dir.exists():
            return []
        return sorted(self.problems_dir.glob("*.json"))

    def load_all_problems(self) -> list[ProblemCreate]:
        """Load and validate all problem definitions found in the problems directory.

        Returns:
            List of validated ProblemCreate schema objects.
        """
        problems: list[ProblemCreate] = []
        for file_path in self.list_problem_files():
            problem = self.load_problem_file(file_path)
            problems.append(problem)

        logger.info("Successfully loaded and validated %d problems", len(problems))
        return problems

    def load_rubric_file(self, file_path: Path) -> RubricCreate:
        """Parse and validate a rubric definition JSON file.

        Args:
            file_path: Filesystem path to the rubric JSON file.

        Returns:
            Validated RubricCreate schema instance.

        Raises:
            EntityNotFoundError: If the file does not exist.
            ValidationError: If JSON or schema validation fails.
        """
        if not file_path.is_file():
            logger.error("Rubric file does not exist: %s", file_path)
            raise EntityNotFoundError("RubricFile", str(file_path))

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in rubric file '%s': %s", file_path.name, exc)
            raise ValidationError(
                message=f"Rubric file '{file_path.name}' contains invalid JSON syntax.",
                details={"file": str(file_path), "error": str(exc)},
            ) from exc

        try:
            rubric = RubricCreate.model_validate(data)
        except PydanticValidationError as exc:
            logger.error("Schema validation failed for rubric '%s': %s", file_path.name, exc)
            raise ValidationError(
                message=f"Rubric file '{file_path.name}' failed schema validation.",
                details={"file": str(file_path), "errors": exc.errors()},
            ) from exc

        self._rubric_cache[rubric.name] = rubric
        return rubric

    def load_all_rubrics(self) -> list[RubricCreate]:
        """Load and validate all rubric definition files found in the rubrics directory."""
        if not self.rubrics_dir.exists():
            return []

        rubrics: list[RubricCreate] = []
        for file_path in sorted(self.rubrics_dir.glob("*.json")):
            rubric = self.load_rubric_file(file_path)
            rubrics.append(rubric)

        logger.info("Successfully loaded and validated %d rubrics", len(rubrics))
        return rubrics

    def load_personas(self, file_path: Path | None = None) -> list[InterviewerPersonaConfigSchema]:
        """Load and validate all interviewer personas from the configured JSON file.

        Args:
            file_path: Optional explicit path to personas JSON file.

        Returns:
            List of validated InterviewerPersonaConfigSchema instances.

        Raises:
            EntityNotFoundError: If the persona configuration file is not found.
            ValidationError: If JSON or schema validation fails.
        """
        target_path = file_path or (self.personas_dir / "interviewer_personas.json")
        if not target_path.is_file():
            logger.error("Personas file not found at %s", target_path)
            raise EntityNotFoundError("PersonasFile", str(target_path))

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data: list[dict[str, Any]] = json.load(f)
        except json.JSONDecodeError as exc:
            logger.error("Malformed JSON in personas file '%s': %s", target_path.name, exc)
            raise ValidationError(
                message=f"Personas file '{target_path.name}' contains invalid JSON syntax.",
                details={"file": str(target_path), "error": str(exc)},
            ) from exc

        personas: list[InterviewerPersonaConfigSchema] = []
        for idx, item in enumerate(data):
            try:
                persona = InterviewerPersonaConfigSchema.model_validate(item)
                personas.append(persona)
                self._persona_cache[persona.id] = persona
            except PydanticValidationError as exc:
                logger.error("Persona validation failed at index %d: %s", idx, exc)
                raise ValidationError(
                    message=f"Persona at index {idx} in '{target_path.name}' failed schema validation.",
                    details={"index": idx, "errors": exc.errors()},
                ) from exc

        logger.info("Successfully loaded and validated %d personas", len(personas))
        return personas

    def load_persona_by_id(self, persona_id: str) -> InterviewerPersonaConfigSchema:
        """Find a persona by its unique identifier or persona type."""
        if persona_id in self._persona_cache:
            return self._persona_cache[persona_id]

        personas = self.load_personas()
        for persona in personas:
            if persona.id == persona_id or persona.persona_type == persona_id:
                return persona

        raise EntityNotFoundError("InterviewerPersona", persona_id)

    def clear_cache(self) -> None:
        """Purge all cached problem, rubric, and persona schemas."""
        self._problem_cache.clear()
        self._rubric_cache.clear()
        self._persona_cache.clear()


# Default singleton instance
default_loader = DataLoader()


def load_problem(file_path_or_slug: Path | str) -> ProblemCreate:
    """Convenience helper to load a problem by file path or slug."""
    if isinstance(file_path_or_slug, Path) or (
        isinstance(file_path_or_slug, str) and "/" in file_path_or_slug
    ):
        return default_loader.load_problem_file(Path(file_path_or_slug))
    return default_loader.load_problem_by_slug(str(file_path_or_slug))


def load_all_problems() -> list[ProblemCreate]:
    """Convenience helper to load all available problems."""
    return default_loader.load_all_problems()


def load_rubric(file_path: Path | str) -> RubricCreate:
    """Convenience helper to load a rubric by file path."""
    return default_loader.load_rubric_file(Path(file_path))


def load_all_rubrics() -> list[RubricCreate]:
    """Convenience helper to load all available rubrics."""
    return default_loader.load_all_rubrics()


def load_personas() -> list[InterviewerPersonaConfigSchema]:
    """Convenience helper to load all available personas."""
    return default_loader.load_personas()


def get_problem_by_slug(slug: str) -> ProblemCreate:
    """Convenience helper to retrieve a validated problem by its slug identifier."""
    return default_loader.load_problem_by_slug(slug)

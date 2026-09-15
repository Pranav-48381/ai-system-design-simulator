"""System Design Interview Simulator - Static Data and Seed Package.

Defines filesystem paths, directory locations, and helper loaders for static
problem specifications, evaluation rubrics, tags, and interviewer personas.
"""

from pathlib import Path
from typing import Final

# Root directory for static system design seed data
DATA_DIR: Final[Path] = Path(__file__).resolve().parent

# Specialized subdirectories for data domains
PROBLEMS_DIR: Final[Path] = DATA_DIR / "problems"
RUBRICS_DIR: Final[Path] = DATA_DIR / "rubrics"
TAGS_DIR: Final[Path] = DATA_DIR / "tags"
PERSONAS_DIR: Final[Path] = DATA_DIR / "personas"


def get_data_dir() -> Path:
    """Return the absolute path to the data root directory."""
    return DATA_DIR


def get_problems_dir() -> Path:
    """Return the path to the problem specifications directory."""
    return PROBLEMS_DIR


def get_rubrics_dir() -> Path:
    """Return the path to the evaluation rubrics directory."""
    return RUBRICS_DIR


def get_tags_dir() -> Path:
    """Return the path to the classification tags directory."""
    return TAGS_DIR


def get_personas_dir() -> Path:
    """Return the path to the interviewer personas directory."""
    return PERSONAS_DIR


def list_problem_files() -> list[Path]:
    """List all JSON problem definition files sorted by filename."""
    if not PROBLEMS_DIR.exists():
        return []
    return sorted(PROBLEMS_DIR.glob("*.json"))


__all__ = [
    "DATA_DIR",
    "PERSONAS_DIR",
    "PROBLEMS_DIR",
    "RUBRICS_DIR",
    "TAGS_DIR",
    "get_data_dir",
    "get_personas_dir",
    "get_problems_dir",
    "get_rubrics_dir",
    "get_tags_dir",
    "list_problem_files",
]

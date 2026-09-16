"""System Design Interview Simulator - Database Seeder Service.

Provides asynchronous seeding of core static data including system design problems,
architectural tags, 5-pillar evaluation rubrics, interviewer personas, and demo accounts.
"""

import json
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.constants import (
    ProblemDifficulty,
    ScoringPillar,
    SeniorityLevel,
)
from app.core.logging import get_logger
from app.core.security import hash_password
from app.data import (
    get_personas_dir,
    get_problems_dir,
    get_rubrics_dir,
    list_problem_files,
)
from app.models.problem import SystemDesignProblem
from app.models.rubric import EvaluationRubric, RubricCriterion
from app.models.tag import ProblemTag
from app.models.user import User

logger = get_logger(__name__)


class DatabaseSeeder:
    """Orchestrates database seeding operations from filesystem seed data."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def seed_tags_and_problems(self) -> dict[str, int]:
        """Load and persist problem definitions and architectural tags."""
        problem_files = list_problem_files()
        problems_created = 0
        problems_updated = 0
        tags_created = 0

        # Cache existing tags by name to avoid duplicate queries
        tag_result = await self.session.execute(select(ProblemTag))
        existing_tags: dict[str, ProblemTag] = {
            tag.name: tag for tag in tag_result.scalars().all()
        }

        for file_path in problem_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)

                slug = data["slug"]
                tag_slugs: list[str] = data.get("tag_slugs", [])

                # Ensure all associated tags exist
                problem_tags: list[ProblemTag] = []
                for tag_slug in tag_slugs:
                    if tag_slug not in existing_tags:
                        new_tag = ProblemTag(
                            name=tag_slug,
                            description=f"System design topic: {tag_slug.replace('-', ' ').title()}",
                        )
                        self.session.add(new_tag)
                        await self.session.flush()
                        existing_tags[tag_slug] = new_tag
                        tags_created += 1
                    problem_tags.append(existing_tags[tag_slug])

                # Check if problem already exists
                stmt = (
                    select(SystemDesignProblem)
                    .options(selectinload(SystemDesignProblem.tags))
                    .where(SystemDesignProblem.slug == slug)
                )
                existing_prob_res = await self.session.execute(stmt)
                existing_problem = existing_prob_res.scalar_one_or_none()

                difficulty_val = ProblemDifficulty(data.get("difficulty", "medium"))

                if existing_problem is None:
                    new_problem = SystemDesignProblem(
                        slug=slug,
                        title=data["title"],
                        summary=data["summary"],
                        description=data["description"],
                        difficulty=difficulty_val,
                        functional_requirements=data.get("functional_requirements", []),
                        non_functional_requirements=data.get("non_functional_requirements", []),
                        scale_targets=data.get("scale_targets", {}),
                        key_challenges=data.get("key_challenges", []),
                        reference_solution=data.get("reference_solution"),
                        is_active=True,
                    )
                    new_problem.tags = problem_tags
                    self.session.add(new_problem)
                    problems_created += 1
                else:
                    # Update fields
                    existing_problem.title = data["title"]
                    existing_problem.summary = data["summary"]
                    existing_problem.description = data["description"]
                    existing_problem.difficulty = difficulty_val
                    existing_problem.functional_requirements = data.get("functional_requirements", [])
                    existing_problem.non_functional_requirements = data.get("non_functional_requirements", [])
                    existing_problem.scale_targets = data.get("scale_targets", {})
                    existing_problem.key_challenges = data.get("key_challenges", [])
                    existing_problem.reference_solution = data.get("reference_solution")
                    existing_problem.tags = problem_tags
                    problems_updated += 1

            except Exception as exc:
                logger.error("Failed to seed problem file '%s': %s", file_path.name, exc)
                raise

        await self.session.flush()
        logger.info(
            "Seeded problems: %d created, %d updated, %d tags created",
            problems_created,
            problems_updated,
            tags_created,
        )
        return {
            "problems_created": problems_created,
            "problems_updated": problems_updated,
            "tags_created": tags_created,
        }

    async def seed_rubrics(self) -> dict[str, int]:
        """Load and persist 5-pillar evaluation rubrics and criteria."""
        rubrics_dir = get_rubrics_dir()
        rubrics_created = 0
        criteria_created = 0

        if not rubrics_dir.exists():
            return {"rubrics_created": 0, "criteria_created": 0}

        rubric_files = sorted(rubrics_dir.glob("*.json"))

        for file_path in rubric_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data: dict[str, Any] = json.load(f)

                rubric_name = data["name"]
                stmt = (
                    select(EvaluationRubric)
                    .options(selectinload(EvaluationRubric.criteria))
                    .where(EvaluationRubric.name == rubric_name)
                )
                res = await self.session.execute(stmt)
                existing_rubric = res.scalar_one_or_none()

                if existing_rubric is None:
                    new_rubric = EvaluationRubric(
                        name=rubric_name,
                        description=data["description"],
                        is_default=data.get("is_default", False),
                    )
                    self.session.add(new_rubric)
                    await self.session.flush()
                    rubrics_created += 1

                    for crit_data in data.get("criteria", []):
                        criterion = RubricCriterion(
                            rubric_id=new_rubric.id,
                            pillar=ScoringPillar(crit_data["pillar"]),
                            title=crit_data["title"],
                            description=crit_data["description"],
                            weight=float(crit_data.get("weight", 1.0)),
                            level_expectations=crit_data.get("level_expectations", {}),
                        )
                        self.session.add(criterion)
                        criteria_created += 1
                else:
                    logger.info("Rubric '%s' already exists, skipping creation", rubric_name)

            except Exception as exc:
                logger.error("Failed to seed rubric file '%s': %s", file_path.name, exc)
                raise

        await self.session.flush()
        logger.info("Seeded rubrics: %d created, %d criteria created", rubrics_created, criteria_created)
        return {
            "rubrics_created": rubrics_created,
            "criteria_created": criteria_created,
        }

    async def seed_default_users(self) -> dict[str, int]:
        """Seed initial demo and administrator user accounts if not present."""
        users_created = 0
        default_accounts = [
            {
                "email": "demo.candidate@example.com",
                "name": "Alex Candidate",
                "password": "Password123!",
                "seniority_level": SeniorityLevel.SENIOR,
                "is_admin": False,
            },
            {
                "email": "admin@example.com",
                "name": "System Administrator",
                "password": "AdminSecurePassword123!",
                "seniority_level": SeniorityLevel.PRINCIPAL,
                "is_admin": True,
            },
        ]

        for acc in default_accounts:
            stmt = select(User).where(User.email == acc["email"])
            res = await self.session.execute(stmt)
            existing_user = res.scalar_one_or_none()

            if existing_user is None:
                new_user = User(
                    email=acc["email"],
                    name=acc["name"],
                    hashed_password=hash_password(acc["password"]),
                    seniority_level=acc["seniority_level"],
                    is_active=True,
                    is_admin=acc["is_admin"],
                )
                self.session.add(new_user)
                users_created += 1

        await self.session.flush()
        logger.info("Seeded default users: %d created", users_created)
        return {"users_created": users_created}

    def load_personas(self) -> list[dict[str, Any]]:
        """Load and return interviewer persona profiles from static JSON configuration."""
        personas_dir = get_personas_dir()
        personas_file = personas_dir / "interviewer_personas.json"

        if not personas_file.exists():
            logger.warning("Interviewer personas configuration file not found at %s", personas_file)
            return []

        with open(personas_file, "r", encoding="utf-8") as f:
            personas_data: list[dict[str, Any]] = json.load(f)

        logger.info("Loaded %d interviewer personas from %s", len(personas_data), personas_file.name)
        return personas_data

    async def seed_all(self) -> dict[str, Any]:
        """Execute complete database seeding workflow inside an atomic transaction."""
        logger.info("Starting complete database seeding sequence...")
        problem_stats = await self.seed_tags_and_problems()
        rubric_stats = await self.seed_rubrics()
        user_stats = await self.seed_default_users()
        personas = self.load_personas()

        await self.session.commit()
        logger.info("Database seeding successfully completed!")

        return {
            **problem_stats,
            **rubric_stats,
            **user_stats,
            "personas_loaded": len(personas),
        }


async def seed_database(session: AsyncSession) -> dict[str, Any]:
    """Convenience functional interface to execute complete database seeding."""
    seeder = DatabaseSeeder(session)
    return await seeder.seed_all()

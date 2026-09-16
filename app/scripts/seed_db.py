#!/usr/bin/env python3
"""System Design Interview Simulator - Database Seeder CLI Runner.

CLI command runner for executing database seeding of problems, tags, rubrics,
interviewer personas, and default test accounts.

Usage:
    python -m app.scripts.seed_db [--all] [--problems-only] [--rubrics-only] [--users-only]
"""

import argparse
import asyncio
import logging
import sys
import time
from typing import Any

from app.core.logging import get_logger, setup_logging
from app.db.session import get_async_session_context
from app.services.seeder import DatabaseSeeder

logger = get_logger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Parse and return command-line arguments for database seeding."""
    parser = argparse.ArgumentParser(
        description="Seed database with system design problems, rubrics, tags, and demo accounts.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--all",
        action="store_true",
        default=True,
        help="Seed all data entities (problems, tags, rubrics, users).",
    )
    parser.add_argument(
        "--problems-only",
        action="store_true",
        help="Only seed system design problem definitions and classification tags.",
    )
    parser.add_argument(
        "--rubrics-only",
        action="store_true",
        help="Only seed evaluation rubrics and competency criteria.",
    )
    parser.add_argument(
        "--users-only",
        action="store_true",
        help="Only seed default candidate and admin accounts.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose DEBUG logging output.",
    )
    return parser.parse_args()


def print_banner() -> None:
    """Print an informative visual banner to console."""
    print("=" * 70)
    print("   AI SYSTEM DESIGN INTERVIEW SIMULATOR - DATABASE SEED RUNNER    ")
    print("=" * 70)


def print_summary_table(stats: dict[str, Any], duration_ms: float) -> None:
    """Print a clean execution summary table of seeded entities."""
    print("-" * 70)
    print(f"{'Entity Category':<35} | {'Count / Status':<30}")
    print("-" * 70)
    for key, value in stats.items():
        label = key.replace("_", " ").title()
        print(f"{label:<35} | {str(value):<30}")
    print("-" * 70)
    print(f"Seeding completed successfully in {duration_ms:.2f}ms.")
    print("=" * 70)


async def run_seeder(args: argparse.Namespace) -> int:
    """Execute asynchronous database seeding according to parsed arguments."""
    start_time = time.perf_counter()
    print_banner()

    stats: dict[str, Any] = {}

    try:
        async with get_async_session_context() as session:
            seeder = DatabaseSeeder(session)

            if args.problems_only:
                logger.info("Executing problems-only seeding...")
                problem_stats = await seeder.seed_tags_and_problems()
                stats.update(problem_stats)
                await session.commit()
            elif args.rubrics_only:
                logger.info("Executing rubrics-only seeding...")
                rubric_stats = await seeder.seed_rubrics()
                stats.update(rubric_stats)
                await session.commit()
            elif args.users_only:
                logger.info("Executing users-only seeding...")
                user_stats = await seeder.seed_default_users()
                stats.update(user_stats)
                await session.commit()
            else:
                # Default: Seed all entities
                logger.info("Executing full database seeding...")
                all_stats = await seeder.seed_all()
                stats.update(all_stats)

        duration_ms = (time.perf_counter() - start_time) * 1000.0
        print_summary_table(stats, duration_ms)
        return 0

    except Exception as exc:
        logger.critical("Fatal error during database seeding: %s", exc, exc_info=True)
        print(f"\n[ERROR] Seeding failed with exception: {exc}", file=sys.stderr)
        return 1


def main() -> None:
    """Synchronous entry point wrapping async execution."""
    args = parse_arguments()
    log_level = logging.DEBUG if args.verbose else logging.INFO
    setup_logging(log_level=log_level)

    exit_code = asyncio.run(run_seeder(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()

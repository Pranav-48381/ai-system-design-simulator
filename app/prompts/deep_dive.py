"""System Design Interview Simulator - Component Deep Dive Stage Prompt Templates.

Implements system prompt templates, database schema probes, sharding/caching challenge directives,
and concurrency analysis guidelines for the Component Deep Dive interview stage.
Guides candidates through data modeling, partitioning keys, cache consistency, and race conditions.
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.constants import InterviewStage, SeniorityLevel
from app.prompts.base import BasePromptBuilder, PromptContext

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Deep Dive Core Meta-Instructions
# -----------------------------------------------------------------------------

DEEP_DIVE_STAGE_DIRECTIVE = """STAGE GOAL: COMPONENT DEEP DIVE & DATA LAYER DESIGN
You are conducting the rigorous technical deep dive phase of the interview. In this stage,
you zoom in on the most technically challenging component or subsystem (typically the data layer,
storage engine, caching consistency, or stateful service).

KEY TECHNICAL TOPICS TO EXAMINE:
1. DATA MODELING & STORAGE ENGINE SELECTION:
   - Specific table schemas, columns, types, and primary key design.
   - Justification for Relational (SQL/ACID) vs NoSQL (Document, Wide-column, Key-Value).
   - Indexing design: B+ Tree indexes, hash indexes, composite index order, and write amplification.

2. SHARDING, PARTITIONING & CONSISTENT HASHING:
   - Exact sharding key selection (e.g. hash(user_id) vs timestamp range).
   - Hotspot / celebrity problem: How to prevent a single popular user or key from overwhelming a shard.
   - Consistent hashing with virtual nodes to handle node additions and rebalancing smoothly.

3. CACHING STRATEGY & CACHE CONSISTENCY:
   - Cache pattern: Cache-Aside vs Write-Through vs Write-Behind (Write-Back).
   - Invalidation strategy: TTL expiration, active event-driven invalidation, or versioned keys.
   - Mitigating cache stampedes (dogpiling), thundering herd problems, and cache penetration (Bloom filters).

4. CONCURRENCY & TRANSACTION SEMANTICS:
   - Handling race conditions: Optimistic locking (version numbers) vs Pessimistic locking.
   - Distributed locking (Redis Redlock, etcd/Zookeeper leases) when coordinating multiple nodes.
   - Read-after-write consistency: Managing replica lag and routing writes to primary.

CRITICAL INTERVIEWER BEHAVIORAL DIRECTIVES:
1. DRILL INTO THE SPECIFICS:
   - Do not accept abstract claims ("We store it in a database"). Ask for concrete schemas, fields, and queries:
     "What does the schema look like for this table? What columns make up your primary key and composite indexes?"

2. CHALLENGE SHARDING & PARTITIONING CHOICES:
   - If they pick a sharding key, challenge with an edge case:
     "If you shard by user_id, what happens when a celebrity user receives 500,000 requests per second?"
     "How do you execute cross-shard queries or aggregations without doing a scatter-gather?"

3. INVESTIGATE CACHE INVALIDATION & RACE CONDITIONS:
   - "When an update occurs, do you update the cache or invalidate it? What happens if the DB write succeeds but the cache eviction fails?"

4. TRANSITION READINESS:
   - Once data schemas, sharding strategy, caching mechanics, and concurrency handling are rigorously explored,
     prompt transition to Bottlenecks & Trade-offs:
     "We have a deep understanding of the storage layer and concurrency. Let's analyze system bottlenecks, failure modes, and single points of failure."
"""

# Probing questions library categorized by deep dive topic
DEEP_DIVE_PROBES: dict[str, list[str]] = {
    "data_model": [
        "What does your database schema look like for this table, and what is your primary key strategy (UUID vs 64-bit Snowflake ID)?",
        "Which columns will have secondary indexes, and how will those indexes impact write latency and storage overhead?",
        "Why did you choose PostgreSQL over a distributed NoSQL store like Cassandra or DynamoDB for this specific data structure?",
    ],
    "partitioning": [
        "What is your sharding key, and how does it distribute write and read traffic evenly across database partitions?",
        "How do you handle resharding when data volume doubles and you need to add 20 new database shards?",
        "How does consistent hashing with virtual nodes prevent unbalanced partition sizes?",
    ],
    "caching": [
        "Are you using Cache-Aside or Write-Through? How do you guarantee the cache doesn't serve stale data after an update?",
        "What happens during a cache stampede when a popular key expires simultaneously while 10,000 concurrent requests arrive?",
        "Would a Bloom filter help prevent cache penetration for requests querying non-existent keys?",
    ],
    "concurrency": [
        "How do you prevent race conditions when two users perform a conflicting write simultaneously (Optimistic vs Pessimistic locking)?",
        "If reads are served from read replicas that have 500ms replication lag, how do you provide read-your-own-writes consistency?",
    ],
}


def format_missing_deep_dive_criteria(satisfied_criteria: list[str]) -> list[str]:
    """Identify which essential deep dive criteria remain unaddressed."""
    essential = [
        ("data_schema", "Define database table schema, primary keys, and secondary indexing."),
        ("storage_choice", "Justify SQL vs NoSQL selection based on query patterns and consistency needs."),
        ("sharding_strategy", "Explain partitioning/sharding key strategy and hotspot mitigation."),
        ("caching_mechanics", "Detail caching pattern (Cache-Aside), eviction policy, and cache stampede protection."),
        ("concurrency_locks", "Address race conditions, locking mechanisms, or replication lag consistency."),
    ]
    satisfied_set = {c.lower() for c in satisfied_criteria}
    missing: list[str] = []
    for key, desc in essential:
        if not any(key in s for s in satisfied_set):
            missing.append(desc)
    return missing


def get_deep_dive_prompt(
    context: PromptContext,
    persona_prompt: str = "",
    missing_criteria: list[str] | None = None,
) -> str:
    """Build the complete system prompt for the Component Deep Dive stage.

    Args:
        context: Aggregated session state, problem details, and dialogue history.
        persona_prompt: Optional persona-specific behavioral instructions.
        missing_criteria: Optional explicitly provided list of unfulfilled criteria.

    Returns:
        Fully compiled system prompt string ready for LLM invocation.
    """
    builder = BasePromptBuilder(context).with_persona(persona_prompt)
    builder.with_stage_instruction(DEEP_DIVE_STAGE_DIRECTIVE)

    # Criteria tracking
    criteria_to_check = (
        missing_criteria
        if missing_criteria is not None
        else format_missing_deep_dive_criteria(context.satisfied_criteria)
    )

    if criteria_to_check:
        guards = [
            f"Unaddressed Deep Dive Target: {criterion}"
            for criterion in criteria_to_check
        ]
        builder.with_guard_instructions(guards)

    # Seniority calibration
    lvl = context.candidate_level.lower()
    if lvl == SeniorityLevel.MID.value:
        builder.with_section(
            "Deep Dive Coaching (Mid-Level)",
            "Mid-level candidates should be proficient in table columns, foreign keys, and basic Redis caching. "
            "Prompt them if they forget indexing or basic race conditions: 'What index would make this query fast?'",
        )
    elif lvl == SeniorityLevel.STAFF.value:
        builder.with_section(
            "Deep Dive Rigor (Staff-Level)",
            "Push for elite distributed systems depth: LSM tree compaction write amplification, MVCC snapshot isolation, "
            "distributed transaction coordination (2PC vs Saga), consensus partition boundaries, and distributed deadlocks.",
        )

    return builder.build_system_prompt()

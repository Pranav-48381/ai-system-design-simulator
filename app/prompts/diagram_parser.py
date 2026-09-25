"""System Design Interview Simulator - Diagram Parser Prompt Templates.

Implements system prompt templates, few-shot examples, and extraction guidelines
for parsing candidate Mermaid diagrams, ASCII text art, and whiteboard topology into
structured DiagramNodeSchema and DiagramEdgeSchema models with architectural validation.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.schemas.canvas import DiagramEdgeTypeEnum, DiagramNodeTypeEnum

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Diagram Parser System Prompt Foundation
# -----------------------------------------------------------------------------

DIAGRAM_PARSER_SYSTEM_PROMPT = """You are an expert Systems Architecture Diagram Parser and Topology Analyzer.
Your responsibility is to parse candidate-submitted architecture diagrams (Mermaid flowchart, sequence diagrams,
or ASCII art) and extract a fully structured graph topology consisting of typed nodes and directed edges.

PARSING OBJECTIVES:
1. EXTRACT ARCHITECTURAL NODES:
   - Identify each distinct component and classify its node_type into one of:
     * "client": Mobile apps, Web browsers, IoT devices, Third-party callers.
     * "load_balancer": NGINX, HAProxy, AWS ALB/NLB, Cloudflare LB.
     * "api_gateway": Kong, Envoy, AWS API Gateway, Zuul, Traefik.
     * "service": Microservices, Backend workers, Stream processors.
     * "database": PostgreSQL, MySQL, Cassandra, MongoDB, DynamoDB, CockroachDB.
     * "cache": Redis, Memcached, Hazelcast, CDN Edge Cache.
     * "queue": Kafka, RabbitMQ, SQS, Google Pub/Sub, Pulsar.
     * "storage": S3, GCS, Blob storage, HDFS, EFS.
     * "cdn": Cloudflare, CloudFront, Fastly, Akamai.
     * "custom": Unclassified custom components.
   - Detect explicit or implied technologies (e.g. "PostgreSQL", "Redis", "Kafka", "Go Microservice").

2. EXTRACT COMMUNICATION EDGES:
   - Identify source_node_id, target_node_id, and edge_type:
     * "sync_http": REST, HTTPS, GraphQL synchronous calls.
     * "async_message": Publish/subscribe, queue producer/consumer, event streams.
     * "grpc": Inter-service RPC or Protobuf streaming.
     * "websocket": Persistent bi-directional client-server connections.
     * "database_query": SQL/NoSQL read/write queries, connection pool traffic.
     * "replication": Primary-to-replica binlog, Raft/Paxos consensus replication.
   - Note communication labels (e.g. "HTTPS /v1/upload", "Publish NewPostEvent").

3. TOPOLOGY & ANTI-PATTERN VALIDATION:
   - Flag high-risk anti-patterns:
     * Direct client-to-database connections without application/gateway layer.
     * Lack of load balancers or gateways ahead of backend stateless tiers.
     * Disconnected / orphan components without input or output traffic.
     * Synchronous blocking RPC chains with cascading latency risks.

STRICT JSON OUTPUT FORMAT:
You MUST respond with a single, valid JSON object containing NO surrounding prose or markdown formatting outside the JSON code block.
Schema:
{
  "title": "<inferred diagram title>",
  "cleaned_mermaid": "<valid, syntactically clean Mermaid flowchart TD code>",
  "nodes": [
    {
      "id": "<unique snake_case or kebab-case identifier, e.g. api_gateway>",
      "label": "<display name on diagram, e.g. Kong API Gateway>",
      "node_type": "<client | load_balancer | api_gateway | service | database | cache | queue | storage | cdn | custom>",
      "technology": "<technology name or null>"
    }
  ],
  "edges": [
    {
      "id": "<edge identifier, e.g. edge_client_lb>",
      "source_node_id": "<matching node id>",
      "target_node_id": "<matching node id>",
      "label": "<protocol or route description or null>",
      "edge_type": "<sync_http | async_message | grpc | websocket | database_query | replication>",
      "is_bidirectional": <boolean>
    }
  ],
  "detected_anti_patterns": [
    "<concise warning about architectural risk, e.g. Direct DB connection from mobile client>"
  ],
  "architectural_insights": "<2-sentence technical summary of the topological flow>"
}
"""

# -----------------------------------------------------------------------------
# Few-Shot Reference Examples
# -----------------------------------------------------------------------------

DIAGRAM_PARSER_FEW_SHOT_EXAMPLES: list[dict[str, Any]] = [
    {
        "input": """
flowchart TD
    Client[Mobile App] -->|HTTPS POST /url| LB[AWS ALB]
    LB --> API[URL Shortener Service]
    API --> Cache[(Redis Cache)]
    API --> DB[(PostgreSQL Primary)]
    DB -.->|WAL Replication| Replica[(PostgreSQL Read Replica)]
    API --> Queue>Kafka Event Bus]
    Queue --> Analytics[Analytics Consumer Worker]
        """,
        "output": {
            "title": "URL Shortener Scalable Architecture",
            "cleaned_mermaid": "flowchart TD\n    Client[Mobile App] -->|HTTPS POST /url| LB[AWS ALB]\n    LB --> API[URL Shortener Service]\n    API --> Cache[(Redis Cache)]\n    API --> DB[(PostgreSQL Primary)]\n    DB -.->|WAL Replication| Replica[(PostgreSQL Read Replica)]\n    API --> Queue>Kafka Event Bus]\n    Queue --> Analytics[Analytics Consumer Worker]",
            "nodes": [
                {"id": "client", "label": "Mobile App", "node_type": "client", "technology": "iOS / Android"},
                {"id": "lb", "label": "AWS ALB", "node_type": "load_balancer", "technology": "AWS Application Load Balancer"},
                {"id": "api", "label": "URL Shortener Service", "node_type": "service", "technology": "Go Microservice"},
                {"id": "cache", "label": "Redis Cache", "node_type": "cache", "technology": "Redis Cluster"},
                {"id": "db", "label": "PostgreSQL Primary", "node_type": "database", "technology": "PostgreSQL"},
                {"id": "replica", "label": "PostgreSQL Read Replica", "node_type": "database", "technology": "PostgreSQL"},
                {"id": "queue", "label": "Kafka Event Bus", "node_type": "queue", "technology": "Apache Kafka"},
                {"id": "analytics", "label": "Analytics Consumer Worker", "node_type": "service", "technology": "Python Worker"},
            ],
            "edges": [
                {"id": "edge_client_lb", "source_node_id": "client", "target_node_id": "lb", "label": "HTTPS POST /url", "edge_type": "sync_http", "is_bidirectional": False},
                {"id": "edge_lb_api", "source_node_id": "lb", "target_node_id": "api", "label": "Internal HTTP", "edge_type": "sync_http", "is_bidirectional": False},
                {"id": "edge_api_cache", "source_node_id": "api", "target_node_id": "cache", "label": "Cache-Aside Query", "edge_type": "database_query", "is_bidirectional": False},
                {"id": "edge_api_db", "source_node_id": "api", "target_node_id": "db", "label": "SQL Write", "edge_type": "database_query", "is_bidirectional": False},
                {"id": "edge_db_replica", "source_node_id": "db", "target_node_id": "replica", "label": "WAL Streaming", "edge_type": "replication", "is_bidirectional": False},
                {"id": "edge_api_queue", "source_node_id": "api", "target_node_id": "queue", "label": "Produce ClickEvent", "edge_type": "async_message", "is_bidirectional": False},
                {"id": "edge_queue_analytics", "source_node_id": "queue", "target_node_id": "analytics", "label": "Consume Events", "edge_type": "async_message", "is_bidirectional": False},
            ],
            "detected_anti_patterns": [],
            "architectural_insights": "Clean tiered architecture with load balancing, caching layer, primary-replica database replication, and decoupled asynchronous queue ingestion.",
        },
    },
]

# -----------------------------------------------------------------------------
# Prompt Builders
# -----------------------------------------------------------------------------

def get_diagram_parser_prompt(
    diagram_text: str,
    problem_title: str = "",
    existing_nodes: list[dict[str, Any]] | None = None,
) -> str:
    """Compose the prompt for parsing candidate diagram syntax into structured nodes and edges.

    Args:
        diagram_text: Raw candidate text containing Mermaid code or ASCII diagram.
        problem_title: Optional title of the system design problem for domain context.
        existing_nodes: Optional list of previously recognized canvas nodes for incremental updates.

    Returns:
        Fully compiled user prompt string for diagram parsing.
    """
    examples_str = json.dumps(DIAGRAM_PARSER_FEW_SHOT_EXAMPLES, indent=2)
    existing_str = (
        json.dumps(existing_nodes, indent=2)
        if existing_nodes
        else "[No previous diagram nodes registered]"
    )

    return f"""{DIAGRAM_PARSER_SYSTEM_PROMPT}

FEW-SHOT REFERENCE EXAMPLE:
{examples_str}

================================================================================
DIAGRAM PARSING CONTEXT
================================================================================
Problem Domain: {problem_title if problem_title else "Generic Distributed System"}

Existing Canvas Nodes (if updating):
{existing_str}

Candidate Submitted Diagram Input:
\"\"\"
{diagram_text.strip()}
\"\"\"

Parse the candidate diagram into the structured JSON format:"""


def get_diagram_validation_prompt(
    mermaid_code: str,
    problem_title: str = "",
) -> str:
    """Compose a focused prompt for identifying syntax errors and architectural anti-patterns in Mermaid code.

    Args:
        mermaid_code: Raw or cleaned Mermaid diagram syntax string.
        problem_title: Title of the system design problem.

    Returns:
        Prompt string requesting validation findings and syntax fixes.
    """
    return f"""You are a Mermaid diagram validator and Senior Distributed Systems Reviewer.
Problem Domain: {problem_title if problem_title else "Distributed System"}

CANDIDATE MERMAID CODE:
```mermaid
{mermaid_code.strip()}
```

TASK:
1. Check for Mermaid syntax validity (valid delimiters, supported keywords: flowchart, graph, sequenceDiagram).
2. Check for distributed systems anti-patterns (missing load balancers, direct client-to-DB calls, circular sync dependencies).
3. If syntax has errors, provide a corrected Mermaid code block.

STRICT JSON OUTPUT FORMAT:
{{
  "is_syntax_valid": <boolean>,
  "syntax_errors": ["<list of syntax errors if any>"],
  "corrected_mermaid": "<corrected valid mermaid code string>",
  "architectural_critique": [
    "<architectural flaw or recommendation 1>",
    "<recommendation 2>"
  ]
}}"""


def get_ascii_to_mermaid_prompt(ascii_diagram: str) -> str:
    """Compose a prompt for translating unstructured ASCII block diagrams into standard Mermaid flowchart syntax.

    Args:
        ascii_diagram: Raw ASCII / text art layout of components and arrows.

    Returns:
        Prompt string requesting standard Mermaid translation.
    """
    return f"""You are an expert at converting ASCII art architecture diagrams into clean Mermaid flowchart TD syntax.

INPUT ASCII DIAGRAM:
\"\"\"
{ascii_diagram.strip()}
\"\"\"

Convert the ASCII diagram into a clean, modern, valid Mermaid `flowchart TD` block.
Use clear node shapes:
- Services/Apps: `[Service Name]`
- Databases: `[(Database Name)]`
- Queues: `>Queue Name]`
- Clients: `([Client Device])`

Respond with ONLY the Mermaid code block starting with ```mermaid and ending with ```:"""

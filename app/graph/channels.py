"""System Design Interview Simulator - LangGraph Channels & State Reducers.

Provides custom state channel reducers, whiteboard canvas synchronization logic,
Mermaid diagram synthesis, and artifact versioning helpers for LangGraph execution.
"""

from collections.abc import Sequence
import re
import time
from typing import Any, Callable

from app.core.constants import ArtifactType, InterviewStage
from app.graph.state import (
    append_list_reducer,
    append_messages_reducer,
    append_unique_list,
    merge_dict_list,
    merge_dict_reducer,
)


def canvas_channel_reducer(
    existing: dict[str, Any] | None,
    update: dict[str, Any] | None,
) -> dict[str, Any]:
    """Custom reducer for the whiteboard canvas state channel.

    Handles monotonic version increments, node upserts/deletions, edge connections,
    and bi-directional synchronization between structured nodes and Mermaid syntax.

    Args:
        existing: Current canvas state dictionary or None.
        update: Incoming partial canvas state or action delta.

    Returns:
        Consolidated and synchronized canvas state dictionary.
    """
    if not existing and not update:
        return {
            "version": 1,
            "title": "System Architecture Diagram",
            "mermaid_code": "",
            "nodes": [],
            "edges": [],
            "viewport": {"zoom": 1.0, "x": 0.0, "y": 0.0},
            "last_updated": time.time(),
        }

    if not update:
        return dict(existing or {})

    current = dict(existing or {})
    current.setdefault("version", 1)
    current.setdefault("title", "System Architecture Diagram")
    current.setdefault("nodes", [])
    current.setdefault("edges", [])
    current.setdefault("viewport", {"zoom": 1.0, "x": 0.0, "y": 0.0})
    current.setdefault("mermaid_code", "")

    action = update.get("action")

    # 1. Full state replacement
    if action == "full_replace" or ("nodes" in update and "edges" in update and action is None):
        current["nodes"] = list(update.get("nodes", current["nodes"]))
        current["edges"] = list(update.get("edges", current["edges"]))
        if "title" in update:
            current["title"] = update["title"]
        if "viewport" in update:
            current["viewport"] = dict(update["viewport"])
        if "mermaid_code" in update:
            current["mermaid_code"] = update["mermaid_code"]
        elif current["nodes"]:
            current["mermaid_code"] = generate_mermaid_from_canvas(current)
        current["version"] = max(current.get("version", 1) + 1, int(update.get("version", 0)))
        current["last_updated"] = time.time()
        return current

    # 2. Direct Mermaid syntax update
    if "mermaid_code" in update and not update.get("nodes"):
        code = update["mermaid_code"]
        current["mermaid_code"] = code
        parsed = parse_mermaid_syntax(code)
        if parsed["nodes"]:
            current["nodes"] = parsed["nodes"]
            current["edges"] = parsed["edges"]
        current["version"] = current.get("version", 1) + 1
        current["last_updated"] = time.time()
        return current

    # 3. Incremental node upsert
    if "upsert_nodes" in update:
        existing_nodes = {n["id"]: n for n in current["nodes"] if isinstance(n, dict) and "id" in n}
        for n in update["upsert_nodes"]:
            if isinstance(n, dict) and "id" in n:
                existing_nodes[n["id"]] = n
        current["nodes"] = list(existing_nodes.values())

    # 4. Incremental node deletion
    if "delete_node_ids" in update:
        del_ids = set(update["delete_node_ids"])
        current["nodes"] = [n for n in current["nodes"] if n.get("id") not in del_ids]
        current["edges"] = [
            e for e in current["edges"]
            if e.get("source_node_id") not in del_ids and e.get("target_node_id") not in del_ids
        ]

    # 5. Incremental edge upsert
    if "upsert_edges" in update:
        existing_edges = {e["id"]: e for e in current["edges"] if isinstance(e, dict) and "id" in e}
        for e in update["upsert_edges"]:
            if isinstance(e, dict) and "id" in e:
                existing_edges[e["id"]] = e
        current["edges"] = list(existing_edges.values())

    # 6. Incremental edge deletion
    if "delete_edge_ids" in update:
        del_edge_ids = set(update["delete_edge_ids"])
        current["edges"] = [e for e in current["edges"] if e.get("id") not in del_edge_ids]

    # Update version and timestamp
    current["version"] = current.get("version", 1) + 1
    current["last_updated"] = time.time()

    # Re-synthesize Mermaid representation if nodes/edges changed and no raw code passed
    if "mermaid_code" not in update:
        current["mermaid_code"] = generate_mermaid_from_canvas(current)

    return current


def calculation_channel_reducer(
    existing: Sequence[dict[str, Any]] | None,
    update: dict[str, Any] | Sequence[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    """Custom reducer for quantitative calculations.

    Deduplicates and updates existing calculations by metric name (case-insensitive)
    while appending brand new metrics to the calculations history.

    Args:
        existing: Existing list of calculation records.
        update: Incoming calculation record or list of records.

    Returns:
        Updated list of calculation records.
    """
    if not update:
        return list(existing or [])

    current_list = list(existing or [])
    name_to_index: dict[str, int] = {}
    for idx, calc in enumerate(current_list):
        if isinstance(calc, dict) and "name" in calc:
            name_to_index[str(calc["name"]).strip().lower()] = idx

    incoming = update if isinstance(update, (list, tuple)) else [update]

    for item in incoming:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name", "")).strip().lower()
        if name and name in name_to_index:
            # Update existing calculation in-place
            idx = name_to_index[name]
            updated_entry = dict(current_list[idx])
            updated_entry.update(item)
            current_list[idx] = updated_entry
        else:
            # Append new calculation
            if name:
                name_to_index[name] = len(current_list)
            current_list.append(dict(item))

    return current_list


def artifact_channel_reducer(
    existing: dict[str, Any] | None,
    update: dict[str, Any] | None,
) -> dict[str, Any]:
    """Custom reducer for active architecture artifacts.

    Merges artifacts by key while preserving metadata, creation timestamps,
    and stage contexts.

    Args:
        existing: Existing active artifacts map.
        update: New artifact entries or modifications.

    Returns:
        Consolidated active artifacts dictionary.
    """
    result = dict(existing or {})
    if not update:
        return result

    for k, v in update.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            merged = dict(result[k])
            merged.update(v)
            merged["last_modified"] = time.time()
            result[k] = merged
        else:
            result[k] = v

    return result


def parse_mermaid_syntax(mermaid_str: str) -> dict[str, list[dict[str, Any]]]:
    """Parse simplified Mermaid flowchart syntax into structured nodes and edges.

    Supports statements like:
    - Node definitions: `Client["Web / Mobile Clients"]`
    - Directed arrows: `Client --> Gateway` or `Client -->|HTTPS| Gateway`

    Args:
        mermaid_str: Raw Mermaid diagram code.

    Returns:
        Dictionary containing 'nodes' and 'edges' lists.
    """
    nodes_map: dict[str, dict[str, Any]] = {}
    edges_list: list[dict[str, Any]] = []

    if not mermaid_str:
        return {"nodes": [], "edges": []}

    lines = [line.strip() for line in mermaid_str.strip().splitlines() if line.strip()]

    # Regex to match node definitions: ID["label"] or ID[label] or ID("label") or ID(label)
    node_pattern = re.compile(r'([A-Za-z0-9_\-]+)\s*(?:\["([^"]+)"\]|\[([^\]]+)\]|\("([^"]+)"\)|\(([^)]+)\))')

    # Regex for connections:
    # A -->|label| B
    # A --|label|--> B
    # A -- label --> B
    # A --> B, A -.-> B, A ==> B
    edge_pattern = re.compile(
        r'([A-Za-z0-9_\-]+)\s*(?:-->\s*\|([^|]+)\||--\s*\|([^|]+)\|\s*-->|--\s*([A-Za-z0-9_/\s]+)\s*-->|-->|-.->|==>)\s*([A-Za-z0-9_\-]+)'
    )

    edge_counter = 0

    for line in lines:
        if line.startswith(("graph", "flowchart", "subgraph", "end", "%%")):
            continue

        # 1. Extract any node definitions on this line first
        for match in node_pattern.finditer(line):
            node_id = match.group(1).strip()
            node_label = match.group(2) or match.group(3) or match.group(4) or match.group(5) or node_id
            node_type = "service"
            lower_label = node_label.lower()
            if "client" in lower_label:
                node_type = "client"
            elif "gateway" in lower_label or "lb" in lower_label or "load balancer" in lower_label:
                node_type = "load_balancer"
            elif "db" in lower_label or "database" in lower_label or "postgres" in lower_label:
                node_type = "database"
            elif "cache" in lower_label or "redis" in lower_label:
                node_type = "cache"
            elif "queue" in lower_label or "kafka" in lower_label or "rabbitmq" in lower_label:
                node_type = "queue"

            nodes_map[node_id] = {
                "id": node_id,
                "label": node_label,
                "node_type": node_type,
            }

        # 2. Extract edge connections on this line
        edge_match = edge_pattern.search(line)
        if edge_match:
            source = edge_match.group(1).strip()
            label = (
                edge_match.group(2)
                or edge_match.group(3)
                or edge_match.group(4)
            )
            if label:
                label = label.strip()
            target = edge_match.group(5).strip()

            if source not in nodes_map:
                nodes_map[source] = {"id": source, "label": source, "node_type": "service"}
            if target not in nodes_map:
                nodes_map[target] = {"id": target, "label": target, "node_type": "service"}

            edge_counter += 1
            edges_list.append({
                "id": f"edge-{source}-{target}-{edge_counter}",
                "source_node_id": source,
                "target_node_id": target,
                "label": label,
                "edge_type": "sync_http",
            })


    return {"nodes": list(nodes_map.values()), "edges": edges_list}


def generate_mermaid_from_canvas(canvas_dict: dict[str, Any]) -> str:
    """Synthesize clean Mermaid flowchart syntax from structured canvas nodes and edges.

    Args:
        canvas_dict: Dictionary containing 'nodes' and 'edges' lists.

    Returns:
        Formatted Mermaid diagram code block string.
    """
    nodes = canvas_dict.get("nodes", [])
    edges = canvas_dict.get("edges", [])

    if not nodes and not edges:
        return ""

    lines = ["flowchart TD"]

    # Declare nodes
    for n in nodes:
        if not isinstance(n, dict):
            continue
        n_id = str(n.get("id", "")).replace("-", "_").replace(" ", "_")
        n_label = str(n.get("label") or n.get("id") or "Component")
        # Sanitize double quotes
        n_label_clean = n_label.replace('"', "'")
        lines.append(f'    {n_id}["{n_label_clean}"]')

    # Declare edges
    for e in edges:
        if not isinstance(e, dict):
            continue
        source = str(e.get("source_node_id", "")).replace("-", "_").replace(" ", "_")
        target = str(e.get("target_node_id", "")).replace("-", "_").replace(" ", "_")
        label = e.get("label")

        if source and target:
            if label:
                label_clean = str(label).replace("|", "/")
                lines.append(f"    {source} -->|{label_clean}| {target}")
            else:
                lines.append(f"    {source} --> {target}")

    return "\n".join(lines)


def create_canvas_delta(
    action: str,
    nodes: list[dict[str, Any]] | None = None,
    edges: list[dict[str, Any]] | None = None,
    mermaid_code: str | None = None,
    version: int = 1,
) -> dict[str, Any]:
    """Construct a standardized whiteboard canvas delta payload.

    Args:
        action: Delta operation ('full_replace', 'upsert_nodes', 'delete_node_ids', etc.).
        nodes: Optional list of nodes affected.
        edges: Optional list of edges affected.
        mermaid_code: Optional Mermaid code representation.
        version: Canvas revision counter.

    Returns:
        Structured canvas delta dictionary.
    """
    delta: dict[str, Any] = {"action": action, "version": version, "timestamp": time.time()}
    if nodes is not None:
        delta["nodes"] = nodes
    if edges is not None:
        delta["edges"] = edges
    if mermaid_code is not None:
        delta["mermaid_code"] = mermaid_code
    return delta


# Master channel reducer registry mapping state channel keys to their respective reducers
CHANNEL_REDUCERS: dict[str, Callable[[Any, Any], Any]] = {
    "messages": append_messages_reducer,
    "completed_stages": append_unique_list,
    "active_artifacts": artifact_channel_reducer,
    "artifact_history": append_list_reducer,
    "calculations": calculation_channel_reducer,
    "stage_criteria_satisfied": merge_dict_list,
    "stage_summary_notes": merge_dict_reducer,
    "hints_used": append_list_reducer,
    "evaluations": merge_dict_reducer,
    "feedback_items": append_list_reducer,
}

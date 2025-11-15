"""CLI for Entity Relationship Graph tasks."""

from __future__ import annotations

import argparse
from pathlib import Path
from uuid import UUID

from automation.entity_graph.service import EntityGraph, load_graph

FAILURES_LOG = Path("specs/002-ai-refactor-plan/reports/graph_failures.log")
GRAPH_DIR = Path("storage/ops/ai-refactor/graphs")


def _log_failure(message: str) -> None:
    FAILURES_LOG.parent.mkdir(parents=True, exist_ok=True)
    with FAILURES_LOG.open("a", encoding="utf-8") as handle:
        handle.write(message + "\n")


def graph_sync(args: argparse.Namespace) -> None:
    print(f"graph sync requesting run_id={args.run_id}")
    graph_file = GRAPH_DIR / f"graph_{args.run_id}.json"
    if not graph_file.exists():
        raise FileNotFoundError(f"Graph not found: {graph_file}")
    graph = load_graph(graph_file)
    print(f"Loaded graph {graph.run_id} with {len(graph.nodes)} nodes and {len(graph.edges)} edges")


def graph_verify(args: argparse.Namespace) -> None:
    graph_file = GRAPH_DIR / f"graph_{args.run_id}.json"
    if not graph_file.exists():
        _log_failure(f"verify: missing graph for run {args.run_id}")
        raise FileNotFoundError(f"Graph not found: {graph_file}")
    graph = load_graph(graph_file)
    node_ids = {node.node_id for node in graph.nodes}
    problems: list[str] = []
    for edge in graph.edges:
        if edge.source_id not in node_ids:
            problems.append(f"missing node for edge source {edge.source_id}")
        if edge.target_id not in node_ids:
            problems.append(f"missing node for edge target {edge.target_id}")
    if problems:
        message = f"Graph verify failed for {graph.run_id}: {problems}"
        _log_failure(message)
        raise RuntimeError(message)
    print(f"Graph {graph.run_id} verified with {len(graph.edges)} edges")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Entity graph CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sync = subparsers.add_parser("graph", help="Sync or verify graphs")
    sync.add_argument("run_id", type=UUID, help="Run identifier")
    sync.add_argument("action", choices=["sync", "verify"], help="Action to perform")

    args = parser.parse_args(argv)
    if args.action == "sync":
        graph_sync(args)
    else:
        graph_verify(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

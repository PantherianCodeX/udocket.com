"""LangGraph builders and helpers for automation pipelines."""

from __future__ import annotations

from .analyze_graph import (
    StageBinding,
    build_analyze_graph_v1,
    get_analyze_stage_bindings,
)
from .artifacts import (
    ArtifactWriteResult,
    OpsWriteResult,
    append_audit_log,
    write_json_artifact,
    write_ops_record,
    write_text_artifact,
)
from .compose_graph import build_compose_graph_v1, get_compose_stage_bindings
from .types import (
    AnalyzeGraphState,
    AnalyzeStateAdapter,
    ArtifactRef,
    ComposeGraphState,
    ComposeStateAdapter,
    OpsRecord,
    RunMetadata,
    TypedAnalyzeNodeImpl,
    TypedComposeNodeImpl,
    adapt_analyze_impl,
    adapt_compose_impl,
)

__all__ = [
    "AnalyzeGraphState",
    "AnalyzeStateAdapter",
    "ArtifactRef",
    "ArtifactWriteResult",
    "ComposeGraphState",
    "ComposeStateAdapter",
    "OpsRecord",
    "OpsWriteResult",
    "RunMetadata",
    "StageBinding",
    "TypedAnalyzeNodeImpl",
    "TypedComposeNodeImpl",
    "adapt_analyze_impl",
    "adapt_compose_impl",
    "append_audit_log",
    "build_analyze_graph_v1",
    "build_compose_graph_v1",
    "get_analyze_stage_bindings",
    "get_compose_stage_bindings",
    "write_json_artifact",
    "write_ops_record",
    "write_text_artifact",
]

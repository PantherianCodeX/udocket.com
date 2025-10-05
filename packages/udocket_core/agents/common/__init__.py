# pyright: strict

"""Shared helpers for agent implementations."""

from .azure_client import AzureChatClient, AzureClientConfig
from .io import (
    AnalysisArtifact,
    TranscriptParse,
    TranscriptSegment,
    append_jsonl,
    ensure_dir,
    next_versioned,
    parse_transcript,
    sha256_file,
)
from .base import AnalysisAgent, AnalysisResult
from .normalization import (
    coerce_mapping,
    coerce_mapping_list,
    coerce_sequence,
    sequence_length,
)

__all__: list[str] = [
    "AzureChatClient",
    "AzureClientConfig",
    "AnalysisAgent",
    "AnalysisResult",
    "AnalysisArtifact",
    "append_jsonl",
    "ensure_dir",
    "next_versioned",
    "parse_transcript",
    "sha256_file",
    "TranscriptParse",
    "TranscriptSegment",
    "coerce_sequence",
    "sequence_length",
    "coerce_mapping",
    "coerce_mapping_list",
]

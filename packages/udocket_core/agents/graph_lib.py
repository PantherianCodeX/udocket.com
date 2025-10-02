from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .common import AnalysisArtifact, parse_transcript, ensure_dir, next_versioned, sha256_file


@dataclass(frozen=True)
class GraphConfig:
    schema_version: str = "v1"
    fallback_entity_limit: int = 50

    @classmethod
    def from_env(cls) -> "GraphConfig":  # pragma: no cover - environment hook for future work
        return cls()


@dataclass(frozen=True)
class EntityMention:
    ts: Optional[float]
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {"ts": self.ts, "text": self.text}


@dataclass(frozen=True)
class EntityRecord:
    entity_id: str
    name: str
    type: str
    mentions: Tuple[EntityMention, ...]

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.entity_id,
            "name": self.name,
            "type": self.type,
            "mentions": [mention.to_json() for mention in self.mentions],
        }


@dataclass(frozen=True)
class RelationshipEvidence:
    ts: Optional[float]
    text: str

    def to_json(self) -> Dict[str, Any]:
        return {"ts": self.ts, "text": self.text}


@dataclass(frozen=True)
class RelationshipEdge:
    edge_id: str
    source: str
    target: str
    type: str
    evidence: Tuple[RelationshipEvidence, ...]

    def to_json(self) -> Dict[str, Any]:
        return {
            "id": self.edge_id,
            "source": self.source,
            "target": self.target,
            "type": self.type,
            "evidence": [ev.to_json() for ev in self.evidence],
        }


@dataclass(frozen=True)
class GraphResult:
    status: str
    entities_file: Path
    graph_file: Path
    entities: Tuple[EntityRecord, ...]
    edges: Tuple[RelationshipEdge, ...]
    entities_checksum: str
    graph_checksum: str
    source_transcript: Path
    hint_source: Optional[Path]
    meta_json: Path
    audit_jsonl: Path
    artifacts: Tuple[AnalysisArtifact, AnalysisArtifact]


class GraphAgent:
    ENTITY_ID_PREFIX = "E"
    EDGE_ID_PREFIX = "REL"

    def __init__(self, config: Optional[GraphConfig] = None) -> None:
        self.config = config or GraphConfig.from_env()

    def build(
        self,
        *,
        case_id: str,
        case_dir: Path,
        job_id: str,
        transcript_path: Path,
        hint_path: Optional[Path] = None,
        hint_payload: Optional[Dict[str, Any]] = None,
    ) -> GraphResult:
        transcript_path = Path(transcript_path)
        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript not found at {transcript_path}")

        analysis_dir = case_dir / "analysis"
        ops_dir = case_dir / "ops"
        ensure_dir(analysis_dir)
        ensure_dir(ops_dir)

        entities, edges = self._resolve_entities_and_edges(
            transcript_path=transcript_path,
            hint_path=hint_path,
            hint_payload=hint_payload,
        )

        schema_version = self.config.schema_version

        entities_path = next_versioned(analysis_dir / f"{job_id}__entities_{schema_version}.json")
        graph_path = next_versioned(analysis_dir / f"{job_id}__graph_{schema_version}.json")

        entities_payload = {"entities": [entity.to_json() for entity in entities]}
        graph_payload = {
            "nodes": [
                {"id": entity.entity_id, "label": entity.name, "type": entity.type}
                for entity in entities
            ],
            "edges": [edge.to_json() for edge in edges],
        }

        entities_path.write_text(
            json.dumps(entities_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        graph_path.write_text(
            json.dumps(graph_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        timestamp = (
            datetime.now(timezone.utc)
            .isoformat(timespec="seconds")
            .replace("+00:00", "Z")
        )

        entities_checksum = sha256_file(entities_path)
        graph_checksum = sha256_file(graph_path)

        meta: Dict[str, Any] = {
            "case_id": case_id,
            "job_id": job_id,
            "entities_file": entities_path.name,
            "graph_file": graph_path.name,
            "entities_checksum": entities_checksum,
            "graph_checksum": graph_checksum,
            "entities": len(entities),
            "edges": len(edges),
            "source_transcript": str(transcript_path),
            "schema_version": schema_version,
            "ts": timestamp,
            "status": "ok",
        }
        if hint_path:
            meta["hint_source"] = str(hint_path)

        meta_path = ops_dir / f"{job_id}__graph_log.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

        audit_payload = {
            "ts": timestamp,
            "case_id": case_id,
            "job_id": job_id,
            "entities_file": str(entities_path),
            "graph_file": str(graph_path),
            "entities": len(entities),
            "edges": len(edges),
        }
        if hint_path:
            audit_payload["hint_source"] = str(hint_path)

        audit_path = ops_dir / "ops_graph.jsonl"
        with audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(audit_payload, ensure_ascii=False) + "\n")

        artifacts = (
            AnalysisArtifact(
                kind="entities",
                path=entities_path,
                checksum=entities_checksum,
                metadata={"entities": len(entities), "source_transcript": str(transcript_path)},
            ),
            AnalysisArtifact(
                kind="graph",
                path=graph_path,
                checksum=graph_checksum,
                metadata={
                    "nodes": len(entities),
                    "edges": len(edges),
                    "source_transcript": str(transcript_path),
                },
            ),
        )

        return GraphResult(
            status="ok",
            entities_file=entities_path,
            graph_file=graph_path,
            entities=tuple(entities),
            edges=tuple(edges),
            entities_checksum=entities_checksum,
            graph_checksum=graph_checksum,
            source_transcript=transcript_path,
            hint_source=hint_path,
            meta_json=meta_path,
            audit_jsonl=audit_path,
            artifacts=artifacts,
        )

    def _resolve_entities_and_edges(
        self,
        *,
        transcript_path: Path,
        hint_path: Optional[Path],
        hint_payload: Optional[Dict[str, Any]],
    ) -> Tuple[List[EntityRecord], List[RelationshipEdge]]:
        payload = hint_payload or {}
        if not payload and hint_path and hint_path.exists():
            try:
                payload = json.loads(hint_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}

        entities: Dict[str, EntityRecord] = {}
        edges: List[RelationshipEdge] = []

        if isinstance(payload, dict):
            entities_raw = payload.get("entities")
            if isinstance(entities_raw, Iterable):
                for idx, item in enumerate(entities_raw, start=1):
                    if not isinstance(item, dict):
                        continue
                    entity = self._entity_from_hint(item, idx)
                    if entity:
                        entities[entity.entity_id] = entity

            relations_raw = payload.get("relations")
            if isinstance(relations_raw, Iterable):
                for idx, item in enumerate(relations_raw, start=1):
                    if not isinstance(item, dict):
                        continue
                    edge = self._edge_from_hint(item, idx)
                    if edge:
                        edges.append(edge)
                        if edge.source not in entities:
                            entities[edge.source] = self._placeholder_entity(edge.source)
                        if edge.target not in entities:
                            entities[edge.target] = self._placeholder_entity(edge.target)

        if entities:
            ordered_entities = sorted(entities.values(), key=lambda ent: ent.entity_id)
            return ordered_entities, edges

        parse = parse_transcript(transcript_path)
        token_re = re.compile(r"\b([A-Z][a-zA-Z]{2,})\b")
        tokens = token_re.findall(parse.body_text)
        unique_tokens = sorted(set(tokens))[: self.config.fallback_entity_limit]
        fallback_entities: List[EntityRecord] = []
        for idx, token in enumerate(unique_tokens, start=1):
            entity_id = f"{self.ENTITY_ID_PREFIX}{idx}"
            fallback_entities.append(
                EntityRecord(
                    entity_id=entity_id,
                    name=token,
                    type="OTHER",
                    mentions=(),
                )
            )
        return fallback_entities, []

    def _entity_from_hint(self, payload: Dict[str, Any], index: int) -> Optional[EntityRecord]:
        name = str(payload.get("name") or "").strip()
        if not name:
            return None
        entity_id = str(payload.get("id") or f"{self.ENTITY_ID_PREFIX}{index}").strip()
        type_value = str(payload.get("type") or "OTHER").strip() or "OTHER"
        mentions_data = payload.get("mentions")
        mentions: List[EntityMention] = []
        if isinstance(mentions_data, Iterable):
            for item in mentions_data:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                ts_val = item.get("ts")
                ts = self._coerce_ts(ts_val)
                mentions.append(EntityMention(ts=ts, text=text))
        return EntityRecord(
            entity_id=entity_id,
            name=name,
            type=type_value,
            mentions=tuple(mentions),
        )

    def _edge_from_hint(self, payload: Dict[str, Any], index: int) -> Optional[RelationshipEdge]:
        source_raw = str(payload.get("source") or "").strip()
        target_raw = str(payload.get("target") or "").strip()
        if not source_raw or not target_raw:
            return None
        edge_id = str(payload.get("id") or f"{self.EDGE_ID_PREFIX}-{index}").strip()
        type_value = str(payload.get("type") or "relation").strip() or "relation"
        evidence_payload = payload.get("evidence")
        evidence: List[RelationshipEvidence] = []
        if isinstance(evidence_payload, Iterable):
            for item in evidence_payload:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if not text:
                    continue
                ts = self._coerce_ts(item.get("ts"))
                evidence.append(RelationshipEvidence(ts=ts, text=text))
        return RelationshipEdge(
            edge_id=edge_id,
            source=source_raw,
            target=target_raw,
            type=type_value,
            evidence=tuple(evidence),
        )

    def _placeholder_entity(self, identifier: str) -> EntityRecord:
        return EntityRecord(
            entity_id=identifier,
            name=identifier,
            type="OTHER",
            mentions=(),
        )

    @staticmethod
    def _coerce_ts(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None


__all__ = [
    "GraphAgent",
    "GraphConfig",
    "GraphResult",
    "EntityRecord",
    "RelationshipEdge",
]

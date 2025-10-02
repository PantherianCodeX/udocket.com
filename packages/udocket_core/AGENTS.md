# uDocket — Core Packages (udocket_core) Guide

Scope: `packages/udocket_core/` (agents, audio, storage, logging). This is the core, framework‑agnostic layer consumed by the platform.

## Design
- No Django imports/dependencies here; keep pure Python with careful third‑party usage.
- Deterministic filesystem behavior and explicit APIs; return dataclasses for results.

## Typing expectations
- Mandatory reading: `docs/typing-roadmap.md` and `docs/typing_refactor_plan.md`.
- CI enforces `mypy packages/udocket_core/logging` and `pyright packages/udocket_core/logging`. Keep that package free of `Any` and untyped defs.
- Treat all `packages/udocket_core` modules as the first frontier for strict typing. When editing a file here:
  - Remove legacy `# type: ignore` comments unless documented in the typing roadmap.
  - Replace ad-hoc dicts/lists with `TypedDict`, `dataclass`, or `Protocol` wrappers.
  - Use generic type parameters (`dict[str, str]` etc.) and never return `Any`.
- Prefer precise types (TypedDict/Protocol/dataclasses/Enum) over `Any` and avoid blanket `# type: ignore`.

## Agents
- Implement agents (e.g., `TranscriptionAgent`) in `agents/` and expose typed configs/results. See `agents/transcribe_lib.py:1`.
- Canada‑only Azure regions; validate early.
- Emit:
  - Primary artifact (e.g., transcript text file)
  - Per‑run JSON metadata and human log under case `ops/`
  - Append JSONL audit entries
- Provide helpers for normalization and versioning (e.g., `_next_versioned`, `normalize_audio`).
- Hashing is required: compute SHA‑256 for every artifact produced (text/JSON included) and expose it so platform layers can persist to `CaseArtifact.checksum` and ops JSON.

### Proposed AnalysisAgent contract (future)
- Interface:
  - `run(input: Path, case_id: str, case_dir: Path, job_id: str, **options) -> AnalysisResult`
  - Accept explicit paths/options (no globals), return dataclass with `artifacts: list[Path]`, `meta_path: Path`, `audit_path: Path`, and summary counts.
- Deterministic outputs:
  - Versioned filenames with `<job_id>__<artifact>_vN.ext` pattern; compute SHA‑256 per file.
  - Write per‑run ops JSON and append to agent‑specific audit JSONL stream.
 - File naming contract for transcripts: `transcript/<job_id>__transcript.txt` with a header summarizing case, source, language, region, duration, and a stable footer if needed.
 - When re‑running, do not overwrite: create `_v2`, `_v3` suffixed versions (use `_next_versioned`).

## Audio
- Put ffmpeg/ffprobe interactions behind small functions (`audio/probe.py`, `normalize_audio`).
- Ensure conversion reasons are recorded and target format constants are defined in one place.
 - Target 16 kHz mono WAV (`pcm_s16le`), unless diarization strategy requires otherwise; keep diarization mono for now per roadmap.

## Storage
- Keep cross‑framework path helpers (e.g., tenant case roots) in `storage/paths.py`.
 - Do not assume Django; accept absolute paths and `Path` objects from callers.

## Logging
- Use simple JSONL appenders for audits (`_append_jsonl`) and structured JSON for per‑run meta. Avoid heavyweight logging stacks here.
 - Include `tool/library versions`, `timestamp_utc`, `attempts_used`, and region in meta for provenance; mirror keys consumed by platform telemetry where feasible.

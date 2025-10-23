# JSON Normalization Adoption — Tracking List

This checklist tracks where to adopt the shared helpers from `packages/udocket_core/utils.json.py`:
- `normalize_json_object` — trim keys, optionally drop empty keys and nullish values
- `coerce_json_object` — coerce to JSON shape without dropping data

Prefer `normalize_json_object` for UI/input metadata, provider options, and review records where blanks should be removed. Keep `coerce_json_object` for parsing external files or preserving payloads verbatim.

## Completed
- apps/platform/operations/llm.py
  - Stage map options normalized; metadata normalized on read/write.
- apps/platform/operations/guardian.py
  - Options/credentials normalized; artifact metadata reads/writes normalized.
- apps/platform/operations/task_modules/guardian.py
  - Unreadable/error review records normalized; reduced job meta normalized.

## Candidates — Straightforward (adopt normalize_json_object)
- apps/platform/operations/task_modules/transcribe.py
  - Base meta (`base_meta`), audio meta updates, and reduced meta payloads. Use `normalize_json_object(..., drop_empty_keys=True)` where we currently construct small dicts and coerce.
  - Existing job meta read may remain `coerce_json_object`.
- apps/platform/ui/views/settings.py
  - Organization settings POST value cleanup (already strips strings). Consider `normalize_json_object` for provider metadata before save.
- apps/platform/operations/services/compose.py
  - Any interim metadata assembled from forms/requests (if present). Use `normalize_json_object`.

## Candidates — Investigate First (may keep coerce_json_object)
- packages/udocket_core/llm/runtime.py
  - Runtime coercions are intentionally lossless; keep `coerce_json_object`. Consider targeted normalization only for user-provided options.
- packages/udocket_core/llm/config.py
  - Provider and assignment config parsing must preserve source; retain `coerce_json_object`.
- packages/udocket_core/agents/compose_lib.py
  - Ingestion of summary/timeline/entity JSON. Retain `coerce_*` (avoid dropping data). Normalization could be scoped to UI-provided metadata only.
- apps/platform/operations/services/analysis.py
  - Reading timeline/entity outputs from disk. Preserve payloads (`coerce_*`) to avoid unintentional data loss.

## Search References (current occurrences)
- Ripgrep seeds (representative):
  - packages/udocket_core/llm/runtime.py — multiple `coerce_json_object` uses (intended)
  - packages/udocket_core/llm/config.py — multiple (intended)
  - packages/udocket_core/agents/compose_lib.py — multiple (intended)
  - apps/platform/operations/task_modules/transcribe.py — base/meta candidates
  - apps/platform/operations/services/analysis.py — preserve
  - apps/platform/operations/services/compose.py — review

## Proposed Approach
1) Module-by-module adoption starting with high-churn app modules that handle UI/input metadata (transcribe task, settings flows).
2) For each change, prefer `normalize_json_object(..., drop_empty_keys=True)`; add `drop_nullish_values=True` when blanks should be removed from persisted records.
3) Keep external file parsing on `coerce_json_object` to avoid functional changes.
4) Track progress by checking off items here and adding per-module notes as needed.

## Notes
- Do not switch to normalization in places where audit/ops logs must remain fully verbatim.
- If normalization affects UI conditionals, ensure tests (or manual checks) cover presence/absence of keys relied on by templates.


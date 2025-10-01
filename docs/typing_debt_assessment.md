# Typing Debt Assessment

## Current state
- Running Pyright in strict mode against `packages/udocket_core` reports roughly 32 errors and 361 warnings, demonstrating the gap between our current annotations and the target strong-typing bar.
- Diagnostics cluster around three areas:
  - **Azure OpenAI helpers** (`agents/common/azure_client.py`, `llm/runtime.py`) consume untyped JSON payloads, so Pyright flags `Unknown` access patterns and duplicate defensive checks.
  - **Guardian agent orchestration** (`agents/guardian_lib.py`) calls into chat runtime constructors with drifted signatures, yielding missing/extra-argument errors and `Unknown` cascades.
  - **Transcription callbacks** (`agents/transcribe_lib.py`) accept Azure SDK event objects without annotations, exposing missing parameter types and unsafe handling of optional floats/paths.
- Additional recurring issues include unused imports, deprecated `datetime.utcnow()` usage, and helper functions that still traffic in `dict[str, Any]` for ffprobe and storage metadata.

## Cleanup strategy
1. **Triage by module**
   - Start with `packages/udocket_core/agents/common/azure_client.py`; replace raw dictionary access with `TypedDict` models of Azure responses and expose typed utility functions for downstream consumers.
   - Update `guardian_lib` to match the current signatures of `build_provider_runtime_config`/`build_chat_client`, wrapping provider metadata in dataclasses or protocols to eliminate `Unknown` payloads.
   - Annotate Azure Speech SDK event handlers in `transcribe_lib` using the official types (`speechsdk.SpeechRecognitionEventArgs`, etc.); if imports are heavy, wrap the data in local lightweight dataclasses for tests.
   - Tighten logging/IO helpers with precise container types (`Mapping[str, object]`) and replace deprecated time utilities with timezone-aware alternatives.

2. **Adopt per-module strictness gates**
   - Once a module is clean, add `# pyright: strict` (and enable `mypy: strict = True` in `pyproject.toml` module overrides if needed). This prevents regression without forcing strict mode across the entire repo.
   - Maintain a checklist of strict modules in your PR descriptions so reviewers can ensure future changes honor the stricter contract.

3. **Integrate with feature work**
   - When a feature touches a flagged module, budget time to lift that module—or at least the affected functions—to strict compliance before landing behavioral changes.
   - For untouched legacy areas, schedule dedicated typing sprints that tackle the most error-prone modules first, reducing production risk while steadily shrinking the debt.

## Refactoring guidance
- **Avoid band-aids.** Do not silence warnings with `# type: ignore` unless a tracking issue exists and the comment explains the risk.
- **Enforce invariants via types.** Replace repeated runtime checks with typed parsers that return well-defined dataclasses so later code can trust the payload shape.
- **Document edge cases.** Typed helpers should include docstrings describing the scenarios uncovered during cleanup (streaming vs non-streaming responses, nullable timestamps, etc.).

## Prompt for future work
> *"You are updating `<module>` inside `packages/udocket_core`. Bring the file to Pyright strict compliance before changing behavior: replace `Any`-typed payloads with typed containers, align function signatures with the current runtime contracts, and remove deprecated helpers. As you refactor, factor shared parsing logic into typed utilities, add regression tests that exercise the tightened types, and document any assumptions about SDK responses. Demonstrate that `pyright --level strict <module>` passes (no `reportUnknown*` warnings) and note any remaining gaps that require follow-up."*

## When should typing happen?
- **During refactors:** If you are already touching a module, treat typing as part of the same change so context and tests stay aligned.
- **Dedicated cleanups:** For modules outside active feature work, create focused typing tasks rather than slipping opportunistic edits into unrelated PRs. This keeps reviews manageable while still driving down the error budget.

## Legacy code stance
- Prefer removing obsolete helpers instead of retrofitting types when the functionality itself should be retired. Eliminating dead code is the fastest path to shrinking our typing debt.

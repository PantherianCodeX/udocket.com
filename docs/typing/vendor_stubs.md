# Vendor Stubs Policy

This project keeps a small set of local type stubs to prevent `Any` spillover from third‑party packages and to keep strict islands green.

## When to add a stub

- A strict file (`# pyright: strict`) or a module slated for promotion fails due to missing type information in a third‑party dependency.
- The missing symbols are stable and we only use a small surface area.

Avoid adding stubs when:

- The upstream package already ships `py.typed` or usable `types-` wheels; prefer installing those.
- The API surface is large or unstable; consider refactoring to reduce surface.

## Where to place stubs

- Location: `typings/<package>/.../*.pyi`
- Both pyright and mypy are configured to discover `typings/`:
  - `pyrightconfig.json` includes `typings` in `executionEnvironments[].extraPaths`.
  - `mypy.ini` sets `mypy_path = typings`.

## Authoring guidelines

- Keep the stub minimal: only include the symbols we actually use.
- Prefer precise parameter and attribute types where they are obvious; otherwise use `object` or structural shapes over `Any`.
- Don’t stub methods you don’t need; elide bodies with `...`.
- Add attributes that strict code accesses (e.g., `.urls` on routers, `.data`/`.status_code` on `Response`).
- Keep stubs deterministic and review small. Large stubs are harder to maintain.

## Verifying stubs

- Run `pyright` and `mypy` locally (`make type-baseline`) to confirm diagnostics are resolved.
- Run strict checks for manifest modules (`make type-strict`) and CI will also enforce pragma presence + strict runs.

## Submission checklist

- Reference this document in PR notes when adding a new stub.
- Include a short rationale and link to the code that requires the stub.
- Keep stubs out of application logic; only place under `typings/`.

## Current local stubs

- `azure.cognitiveservices.speech` — minimal surface for the Speech SDK used by the transcription agent.
- `rest_framework.routers`, `rest_framework.request`, `rest_framework.response`, `rest_framework.viewsets`, `rest_framework.permissions`, `rest_framework.authentication`, `rest_framework.exceptions` — minimal DRF stubs for routers, request/response, and auth/permissions surfaces used in strict modules.

If additional gaps come up, follow this policy to extend coverage incrementally.

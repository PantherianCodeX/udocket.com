## Typing Inspector

The `typing_inspector` package collects typing diagnostics from Pyright and mypy and
summarises them into a single manifest that highlights both the current enforcement surface
and the remaining work across the repository.

### Commands

Run a full audit from the repository root:

```bash
python -m typing_inspector audit --max-depth 3
```

This produces `docs/typing/typing_audit_manifest.json` containing:

- All diagnostics from the current enforced configuration (`mode="current"`).
- An expansive run across the project directories (`mode="full"`).
- Aggregated per-file and per-folder summaries with recommendations for enabling stricter checks.

Options:

- `--skip-current` / `--skip-full` – limit runs to the requested modes.
- `--pyright-only` / `--mypy-only` – focus on a single tool.
- `--full-path <path>` – add directories to the full-run command.
- `--manifest <path>` – override the output location.

### Nightly pipeline

The typing nightly workflow invokes the audit and publishes the manifest as a build artifact,
allowing progress tracking without failing the pipeline while the codebase is still being migrated.

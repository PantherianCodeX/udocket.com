# Codex CLI Home Pinning Playbook

This note captures the exact steps to bind the Codex CLI runtime to the `udocket` workspace, following the guidance in `AGENTS.md` and `scripts/codexhome.sh`.

## When to Run
- First time you clone or re-home the repo.
- After moving the working copy or resetting `.codex/.codexhome`.
- Whenever VS Code terminals lose the pinned location (rare, but re-running the script is safe and idempotent).

## Command Sequence
1. From the repo root (`/home/user/Code/udocket`), pin the workspace:
   ```bash
   ./scripts/codexhome.sh .
   ```
   Expected output (paths adjust if you pass a different target):
   ```text
   [codexhome] CODEX_HOME set to: /home/user/Code/udocket/.codex
   [codexhome] To apply immediately in this shell run:
       eval "$(scripts/codexhome.sh --print-export ".")"
   ```
   The script also writes the resolved path to `.codex/.codexhome` so VS Code terminals auto-source it per `.vscode/settings.json`.
2. To activate the setting in your *current* shell session without reopening the terminal, run:
   ```bash
   eval "$(./scripts/codexhome.sh --print-export .)"
   ```
   which expands to:
   ```text
   export CODEX_HOME="/home/user/Code/udocket/.codex"
   ```

## Post-Run Checklist
- `.codex/.codexhome` contains the absolute workspace-coded path.
- Personal Codex state (auth tokens, logs) stays ignored via `.gitignore`—never commit those files.
- VS Code terminal tabs now read the pinned location automatically; rerun the script only if you relocate the repo.

## Troubleshooting
- Passing a different directory (`./scripts/codexhome.sh ~/work/udocket`) repoints the home; use this if you want to share Codex state across sibling clones.
- `--print-export` is safe for shells and CI bootstrap scripts; `AGENTS.md` recommends using it with `eval` when you cannot restart the terminal.

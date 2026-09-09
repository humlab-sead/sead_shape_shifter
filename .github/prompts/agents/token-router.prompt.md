---
agent: ask
description: Route a code task to the smallest useful context before any deeper review or implementation work
---

# Token Router

Use this prompt first for non-trivial code tasks in this repository.

## Goal

Reduce token usage by finding the smallest set of files, rules, and commands needed to answer the task or review the change.

## Required behavior

1. Read the root `AGENTS.md` and only the subtree `AGENTS.md` files needed for the touched area.
2. Prefer `graphify-out/` artifacts and scoped repo navigation over broad source scans.
3. Prefer exact file paths and targeted symbols over whole-directory summaries.
4. Keep the context list short. If a file is not needed to answer the task, exclude it.
5. When shell commands are needed, prefer token-efficient commands and retry without `rtk` only if it is unavailable.

## Routing rules

- For `src/**`, include `src/AGENTS.md`.
- For `backend/**`, include `backend/AGENTS.md`.
- For `frontend/**`, include `frontend/AGENTS.md`.
- For cross-layer work, include only the specific boundary files that connect the layers.
- If the task mentions architecture, dependencies, or call flow, consult `graphify-out/` first.

## Output format

Return only these sections:

1. `Scope`
   - One sentence with the task boundary.
2. `Files To Read`
   - Short list of required files.
3. `Rules To Apply`
   - Short list of repo rules that matter for this task.
4. `Checks To Run`
   - Minimal command list.
5. `Not Needed`
   - Files or areas intentionally excluded.

## Stop conditions

- Do not propose code changes.
- Do not read large files unless they are directly needed.
- Do not restate broad architecture when the task is local.

## Repository references

- `AGENTS.md`
- `graphify-out/wiki/index.md`
- `.github/copilot-instructions.md`
- `Makefile`

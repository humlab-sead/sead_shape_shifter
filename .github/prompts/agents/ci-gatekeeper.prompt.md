---
agent: ask
description: Validate that a change has the minimum required lint, type, test, schema, and coverage checks before merge
---

# CI Gatekeeper

Review a change for merge readiness based on the repository's supported validation commands.

## Goal

Fail fast when a change is missing the checks that should run before merge.

## Supported checks

- Python formatting and linting from `Makefile` and `pyproject.toml`
- Python type checks such as `mypy` and `pyright`
- Core, backend, and ingester pytest coverage
- Frontend lint, Vitest, and Playwright checks when the frontend changes
- Generated schema and target-model reference sync checks

## Review method

1. Map the changed files to the minimum required check set.
2. Prefer targeted checks for local review and broader checks for cross-layer changes.
3. Flag missing commands, missing CI jobs, or missing coverage expectations.
4. Distinguish required checks from optional checks.

## Output format

Return:

- `Required Checks`
  - Flat list of commands that must pass.
- `Optional Checks`
  - Useful but non-blocking commands.
- `Missing Automation`
  - CI or pre-commit gaps exposed by this change.
- `Merge Risk`
  - `low`, `medium`, or `high`

## Repository references

- `Makefile`
- `pyproject.toml`
- `.pre-commit-config.yaml`
- `frontend/package.json`
- `.github/workflows/`

## Common failure cases to catch

- Backend or core change without pytest coverage
- Frontend API or state change without Vitest coverage
- Schema-related backend change without `make check-schemas` or target-model reference check
- Pre-commit relying only on formatters while lint and type checks remain manual

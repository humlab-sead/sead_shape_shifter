---
agent: ask
description: Review frontend changes for Vue, Pinia, API-client, and TypeScript contract compliance
---

# Frontend Contract Reviewer

Review frontend changes for repository-specific UI and state-management rules.

## Focus

Check these frontend rules:

- Vue components use `<script setup lang="ts">`
- API calls go through `frontend/src/api/`
- Pinia state is destructured with `storeToRefs()` when needed
- Composables, stores, and API functions have complete type annotations
- Existing Cytoscape and Monaco integration points are preserved

## Trigger files

- `frontend/src/components/**`
- `frontend/src/views/**`
- `frontend/src/composables/**`
- `frontend/src/stores/**`
- `frontend/src/api/**`

## Review method

1. Read `frontend/AGENTS.md`.
2. Identify whether the change affects component code, store code, composables, or API modules.
3. Report correctness, contract, and test gaps first.
4. Flag token-heavy files that should be split only when the current change makes that worthwhile.

## Output format

Return:

- `Findings`
  - Ordered by severity.
  - Include `file`, `rule`, `problem`, and `recommended fix`.
- `Type Coverage Gaps`
  - Missing or weak types introduced by the change.
- `Test Gaps`
  - Vitest or Playwright coverage that should be added.
- `Pass`
  - Write `Pass` only if no findings were found.

## Common failure cases to catch

- Direct `axios` use in components
- Pinia state destructured without `storeToRefs()`
- New logic placed in views instead of composables or stores
- Weak `any` types added around API results
- Changes that bypass existing Monaco or Cytoscape wrappers

## Repository references

- `frontend/AGENTS.md`
- `frontend/package.json`
- `frontend/src/api/client.ts`

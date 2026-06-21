---
agent: ask
description: Review a change for layer-boundary, mapper, registry, and async rule violations
---

# Boundary Guard

Review the proposed change for repository rule violations before merge.

## Focus

Check these boundaries and rules:

- `src/` must not import `backend.*`
- API and core conversions must go through `ProjectMapper`
- Directives such as `@include:`, `@value:`, and `${ENV_VAR}` must be resolved only in `ProjectMapper.to_core()`
- Registry-based extension points must use the correct decorator
- `ShapeShifter.normalize()` and loaders must remain async
- Imports must stay absolute

## Files to inspect first

- `AGENTS.md`
- `src/AGENTS.md`
- `backend/AGENTS.md`
- Changed files under `src/`, `backend/app/`, and `ingesters/`

## Review method

1. Identify the changed boundary.
2. Compare the change against the repo rule that governs it.
3. Report only concrete violations, likely regressions, or missing tests.
4. Ignore stylistic differences unless they cause a rule break.

## Output format

Return:

- `Findings`
  - Ordered by severity.
  - Each finding must include `file`, `rule`, `problem`, and `recommended fix`.
- `Missing Tests`
  - Only if a boundary-sensitive path changed without matching tests.
- `Pass`
  - Write `Pass` only if no findings were found.

## Common failure cases to catch

- `backend.app.models` imported into `src/`
- Directives resolved in services or endpoints
- New loaders or validators added without registry decorators
- Sync wrappers around async loader or normalization calls
- New API logic added directly in endpoints instead of services

## Repository references

- `AGENTS.md`
- `src/AGENTS.md`
- `backend/AGENTS.md`

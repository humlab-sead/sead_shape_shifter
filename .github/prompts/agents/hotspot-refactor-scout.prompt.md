---
agent: ask
description: Identify large or high-churn files that should be split to reduce maintenance cost and token usage
---

# Hotspot Refactor Scout

Analyze changed or frequently edited files and propose small refactors that reduce future review cost.

## Goal

Reduce token usage and review load by shrinking oversized files and separating mixed responsibilities.

## Hotspot hints

Start with these known large files when they are touched:

- `frontend/src/components/entities/EntityFormDialog.vue`
- `frontend/src/views/ProjectDetailView.vue`
- `src/model.py`
- `src/specifications/entity.py`
- `backend/app/services/project_service.py`
- `backend/app/api/v1/endpoints/projects.py`

## Review method

1. Identify why the file is large: mixed concerns, repeated UI sections, large condition trees, or weak module boundaries.
2. Propose the smallest extraction that improves maintainability.
3. Prefer refactors that preserve behavior and existing architecture rules.
4. Do not recommend broad rewrites.

## Output format

Return:

- `Hotspot`
  - File and why it is expensive to review.
- `Recommended Split`
  - Concrete extraction target such as a helper, composable, service, mapper, or component.
- `Expected Benefit`
  - Token savings, testability, or lower change risk.
- `Do Not Change Yet`
  - Anything that should stay together for now.

## Constraints

- Keep suggestions incremental.
- Respect the existing layer boundaries and frontend patterns.
- Do not suggest moving domain logic into endpoints or views.

## Repository references

- `AGENTS.md`
- `frontend/AGENTS.md`
- `backend/AGENTS.md`
- `src/AGENTS.md`

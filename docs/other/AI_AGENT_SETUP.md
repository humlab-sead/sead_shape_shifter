# AI Agent Setup

This document defines a practical set of repository-local agents for code review, change routing, and token control in `sead_shape_shifter`.

The prompt files live in `.github/prompts/agents/`. Each prompt is narrow on purpose. Use them together instead of building one large general reviewer.

## Agent Files

- `token-router.prompt.md`
- `boundary-guard.prompt.md`
- `pipeline-invariant-reviewer.prompt.md`
- `backend-contract-reviewer.prompt.md`
- `frontend-contract-reviewer.prompt.md`
- `hotspot-refactor-scout.prompt.md`
- `ci-gatekeeper.prompt.md`
- `graph-steward.prompt.md`

## Recommended Trigger Map

### Token Router

- Codex: run first for any task that touches more than one file or crosses layers.
- Copilot: keep as a reusable chat prompt when starting a change or review.
- GitHub Actions: not recommended. This agent is interactive and meant to reduce context before deeper work.

### Boundary Guard

- Codex: run on every PR review that touches `src/`, `backend/app/`, or `ingesters/`.
- Copilot: trigger manually when a change adds loaders, validators, mappers, endpoints, or async service code.
- GitHub Actions: run on `pull_request` for path patterns `src/**`, `backend/app/**`, and `ingesters/**`.

### Pipeline Invariant Reviewer

- Codex: run when the change touches `src/normalizer.py`, `src/model.py`, `src/transforms/**`, `src/loaders/**`, `src/specifications/**`, or `src/target_model/**`.
- Copilot: trigger manually for core pipeline work and bug fixes in normalization behavior.
- GitHub Actions: run on `pull_request` with path filters for the same `src/**` areas.

### Backend Contract Reviewer

- Codex: run when a change touches `backend/app/api/v1/endpoints/**`, `backend/app/models/**`, `backend/app/services/**`, `backend/app/validators/**`, or `backend/app/mappers/**`.
- Copilot: use as a review prompt before merging backend feature work.
- GitHub Actions: run on `pull_request` for `backend/app/**` and `backend/tests/**`.

### Frontend Contract Reviewer

- Codex: run when the change touches `frontend/src/api/**`, `frontend/src/stores/**`, `frontend/src/composables/**`, `frontend/src/components/**`, or `frontend/src/views/**`.
- Copilot: use as a review prompt for Vue, Pinia, Monaco, or Cytoscape changes.
- GitHub Actions: run on `pull_request` for `frontend/src/**` and `frontend/tests/**`.

### Hotspot Refactor Scout

- Codex: run when a PR touches a file above roughly 600 lines, or when a large file is edited in several places.
- Copilot: use manually when a change feels noisy or expensive to review.
- GitHub Actions: run on `pull_request` as an advisory job when changed files exceed a line-count or churn threshold.

### CI Gatekeeper

- Codex: run before handoff on every non-trivial change.
- Copilot: use as a final review prompt before opening a pull request.
- GitHub Actions: run on every `pull_request` and `push` to protected branches.

### Graph Steward

- Codex: run after merges, file moves, large refactors, or architecture changes.
- Copilot: not the best fit unless a user explicitly asks for graph-oriented navigation.
- GitHub Actions: run on `push` to `main` or on a nightly schedule if you want `graphify-out/` to stay current.

## Recommended Execution Order

Use this order for multi-step reviews:

1. `token-router.prompt.md`
2. One or more contract reviewers for the touched area
3. `boundary-guard.prompt.md` for cross-layer changes
4. `ci-gatekeeper.prompt.md`
5. `graph-steward.prompt.md` after merge or after a larger refactor

Use `hotspot-refactor-scout.prompt.md` only when the change touches large files or the review surface is too broad.

## Suggested GitHub Actions Wiring

Use small path-based jobs instead of one large review job.

### Core and boundary review

- Trigger: `pull_request`
- Paths:
  - `src/**`
  - `backend/app/**`
  - `ingesters/**`
  - `AGENTS.md`

Run:

- `boundary-guard.prompt.md`
- `pipeline-invariant-reviewer.prompt.md` when `src/**` changed
- `ci-gatekeeper.prompt.md`

### Backend review

- Trigger: `pull_request`
- Paths:
  - `backend/app/**`
  - `backend/tests/**`

Run:

- `backend-contract-reviewer.prompt.md`
- `ci-gatekeeper.prompt.md`

### Frontend review

- Trigger: `pull_request`
- Paths:
  - `frontend/src/**`
  - `frontend/tests/**`

Run:

- `frontend-contract-reviewer.prompt.md`
- `hotspot-refactor-scout.prompt.md` when a touched frontend file is large
- `ci-gatekeeper.prompt.md`

### Graph maintenance

- Trigger: `push` to `main`
- Optional trigger: nightly schedule

Run:

- update graph artifacts
- `graph-steward.prompt.md`

## Suggested Codex Usage

Use these prompts as explicit review requests in Codex:

- `Review this PR with .github/prompts/agents/boundary-guard.prompt.md`
- `Route this task with .github/prompts/agents/token-router.prompt.md`
- `Review backend contract compliance with .github/prompts/agents/backend-contract-reviewer.prompt.md`
- `Review frontend contract compliance with .github/prompts/agents/frontend-contract-reviewer.prompt.md`

For larger changes, ask Codex to run two or three of these prompts in sequence and keep the result scoped to findings and missing tests.

## Suggested Copilot Usage

Use these prompt files as repo-local chat references rather than trying to make Copilot do all reviews with one instruction file.

Recommended pattern:

1. Start with `token-router.prompt.md`
2. Run the area-specific reviewer
3. End with `ci-gatekeeper.prompt.md`

If Copilot supports slash prompts or reusable prompt files in your editor setup, expose the files in `.github/prompts/agents/` directly.

## First Three To Enable

If you want the smallest useful rollout, enable these first:

1. `token-router.prompt.md`
2. `boundary-guard.prompt.md`
3. `ci-gatekeeper.prompt.md`

That gives you smaller context windows, better rule enforcement, and a cleaner merge gate without adding much process overhead.

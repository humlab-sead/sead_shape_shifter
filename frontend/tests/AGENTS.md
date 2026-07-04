# `frontend/tests/` — Agent Guide

Tests in this directory cover the Vue 3 frontend (`frontend/src/`) using Playwright end-to-end tests.

> Also read the root [`AGENTS.md`](../../AGENTS.md) and [`frontend/AGENTS.md`](../AGENTS.md) for cross-cutting architecture and frontend-specific rules.

## Current status

Playwright e2e tests are currently **disabled**. Existing specs are marked `test.skip` and retained for future re-enablement. Do not remove them.

## Run commands

```bash
pnpm test:e2e              # all tests, headless
pnpm test:e2e:ui           # interactive UI mode (recommended for development)
pnpm test:e2e:headed       # headed mode (see the browser)
make frontend-test         # full frontend test suite via Makefile
```

Test config: `frontend/playwright.config.ts`.

## Directory structure

| File / directory | What it tests |
|---|---|
| `e2e/00-smoke.spec.ts` | Application loads and basic navigation works |
| `e2e/01-project-management.spec.ts` | Project create, read, update, and delete operations |
| `e2e/02-validation-workflow.spec.ts` | Validation run and auto-fix workflows |
| `e2e/03-entity-management.spec.ts` | Entity create, read, update, delete, and data preview |
| `e2e/fixtures/projects.ts` | Sample project configurations used across tests |

## Test patterns

- Use Playwright's `page` fixture for browser interaction — do not import Vue testing utilities here.
- Test from the user's perspective: navigate to a page, interact with the UI, assert on visible outcomes.
- Use the `fixtures/projects.ts` helpers to build consistent test project data rather than duplicating inline configs.
- Keep tests independent: each spec should set up and tear down its own state rather than relying on execution order.
- Use `test.skip` to disable a test temporarily — do not delete specs.

## Scope boundaries

- Tests here validate user-visible frontend behaviour through the browser.
- Unit tests for Vue components, composables, and Pinia stores belong in the frontend unit test suite (configured in `frontend/vitest.config.ts`), not here.
- Backend API logic is tested in `backend/tests/`. Do not duplicate API contract tests in e2e specs.
- The e2e tests require the backend to be running at `VITE_API_BASE_URL` (default `http://localhost:8012`). Check `playwright.config.ts` for the `webServer` setup.

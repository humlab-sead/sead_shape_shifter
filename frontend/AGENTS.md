# Shape Shifter – Frontend (`frontend/`) Agent Rules

Rules here apply when working in `frontend/`. Also read the root `AGENTS.md` for cross-cutting rules.

## Vue 3 Conventions

- Use Composition API with `<script setup lang="ts">` — no Options API.
- Typed props and emits: `defineProps<T>()`, `defineEmits<T>()`.
- Use `storeToRefs()` when destructuring Pinia store state to preserve reactivity.
- Prefer composables over mixins for shared logic.

## State and API

- Application state lives in Pinia stores (`frontend/src/stores/`).
- All backend API calls go through `apiClient` in `frontend/src/api/`.
- Backend endpoints are under `/api/v1`; base URL from `VITE_API_BASE_URL` (default `http://localhost:8012`).

## TypeScript

- Strict null checks — handle `null` and `undefined` explicitly.
- Use `type` for union types; use `interface` for object-shaped API contracts.
- All composables, stores, and API functions must have complete type annotations.

## Tooling

- `pnpm` for all package management — not npm or yarn.
- `make frontend-run` starts dev server (:5173); `make frontend-test` / `make frontend-coverage` for tests.
- `make frontend-lint` before committing.

## Constraints

- Preserve existing patterns unless the task explicitly asks for a larger redesign.
- Graph visualisation uses Cytoscape (`frontend/src/composables/useCytoscape.ts`) — do not swap the library.
- YAML editor uses Monaco — do not swap it.

---
description: "Use when adding or changing a Pinia store in the Vue frontend."
applyTo: "frontend/src/stores/**"
---
# Pinia Stores

- One store per file in `frontend/src/stores/`. Use the setup form: `defineStore('name', () => { ... })`.
- Group the body as state (`ref`), getters (`computed`) and actions (functions), and return everything that callers use.
- Call the backend through the modules in `frontend/src/api/`, not through `axios` or `fetch` in the store.
- Actions that call the backend set a loading flag, clear the error, store a readable message on failure, and reset the flag in `finally`. Follow the existing actions in the same store on whether to rethrow.
- Components that destructure state or getters use `storeToRefs()`. Actions can be destructured directly.
- `frontend/src/stores/index.ts` re-exports only some stores. Import the others from their own file.
- Tests are in `frontend/src/stores/__tests__/`.

## New API Calls

Add the call to a module in `frontend/src/api/` that exports an `<name>Api` object and uses `apiRequest<T>()` from `./client`. Paths are relative to `/api/v1`. Add a new module to the exports and the `api` object in `frontend/src/api/index.ts`.

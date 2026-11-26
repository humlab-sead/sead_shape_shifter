# Shape Shifter – Frontend (`frontend/`) Agent Rules

Rules here apply when working in `frontend/`.

Shared rules are in the root `AGENTS.md`. Rules for particular files are in `.github/instructions/`. Some tools attach them automatically; if yours does not, read the matching file before editing.

| Working on | Read in `.github/instructions/` |
|---|---|
| Vue, TypeScript, API access, state | `frontend.instructions.md` |
| Pinia stores | `frontend-stores.instructions.md` |
| Monaco editors and YAML schemas | `frontend-monaco.instructions.md` |
| Dependency graph views | `features/graph.instructions.md` |
| Vitest tests | `frontend-test.instructions.md` |

## Tooling

- `pnpm` for all package management — not npm or yarn.
- `make frontend-run` starts dev server (:5173); `make frontend-test` / `make frontend-coverage` for tests.
- `make frontend-lint` before committing.

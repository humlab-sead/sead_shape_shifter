# `tests/` — Agent Guide

Tests in this directory cover the Core (`src/`) transformation engine. They are pure Python unit and integration tests with no backend or API dependency.

> Shared rules are in the root [`AGENTS.md`](../AGENTS.md). Rules for writing Python tests are in [`test-writing.instructions.md`](../.github/instructions/test-writing.instructions.md); read it before changing a test. Core rules are listed in [`src/AGENTS.md`](../src/AGENTS.md).

## Run commands

```bash
uv run pytest tests -v                  # full Core suite
uv run pytest tests/process -v          # one subdirectory
uv run pytest tests/test_dispatch.py -v # one file
make test                               # full suite (Core + backend)
```

## Fixtures and test data

- Shared fixtures live in `conftest.py` at this level.
- Static test data files live in `test_data/`.
- Build small inline data structures in tests rather than loading files wherever the test remains readable.
- Mock external I/O (DB connections, file reads, HTTP) at the loader or client boundary, not inside Core domain logic.

## Directory structure

| Directory / file | What it tests |
|---|---|
| `config/`, `configuration/` | Project config loading and resolution |
| `integration/` | End-to-end Core pipeline runs |
| `loaders/` | Data loader implementations (`src/loaders/`) |
| `model/` | Core model classes (`src/model.py`) |
| `process/` | Pipeline stage behaviour (extract, filter, link, unnest, translate, store) |
| `project/` | Project-level specifications and constraint checks |
| `reconciliation/` | Reconciliation domain logic (`src/reconciliation/`) |
| `specifications/` | `ProjectSpecification` subclasses |
| `target_model/` | Target model conformance validators |
| `transforms/` | Transform dispatch and individual transform types |
| `types/` | Type utilities and helpers |
| `validators/` | Domain validators (`src/validators/`) |
| `test_dispatch.py` | Transform dispatch routing |
| `test_mapping.py` | Column and entity mapping |
| `test_path_resolution.py` | Path and file resolution helpers |
| `test_utility.py` | Utility functions |

## Scope boundaries

- Tests here validate Core (`src/`) logic only.
- Backend endpoint and service tests belong in `backend/tests/`.
- Frontend tests belong in `frontend/tests/`.
- Do not duplicate backend integration tests here — if a test needs `TestClient` or `backend.app`, it belongs in `backend/tests/`.

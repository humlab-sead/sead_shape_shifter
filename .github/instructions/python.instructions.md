---
description: "Use when editing Python code in src, backend, ingesters, or tests. Covers configuration data handling and points to the shared architecture and test rules."
applyTo: "src/**/*.py,backend/**/*.py,ingesters/**/*.py,tests/**/*.py"
---
# Python Architecture

Cross-cutting architecture rules, including imports, layers, mappers, directives, registries, circular imports and async calls, are in the root `AGENTS.md`. Docstring wording is under "Documentation Vocabulary" there.

- When transforming configuration data, do not mutate input objects; make deep copies before changing nested values.
- Test conventions for `tests/` and `backend/tests/` are in `test-writing.instructions.md`.

---
description: "Use when adding or modifying ingesters or ingester tests. Covers protocol, discovery, config, and test rules for the top-level ingesters system."
name: "Ingester Development"
applyTo:
  - "ingesters/**/*.py"
  - "backend/tests/ingesters/**/*.py"
---
# Ingester Development

- Implement the protocol from `backend/app/ingesters/protocol.py`.
- Register ingesters with `@Ingesters.register(key=...)`.
- Place ingesters under the top-level `ingesters/<name>/` directory, not under `backend/app/ingesters/`.
- Discovery is automatic via `IngesterRegistry.discover()`; do not add manual imports unless the existing system requires it.
- Use explicit `IngesterConfig` values in tests to avoid `ConfigValue` or `ConfigStore` dependencies.
- Keep `validate()` and `ingest()` responsibilities separate and return structured result types.
- Put ingester-specific settings in `IngesterConfig.extra`.
- Use `ingesters/README.md` and `backend/app/ingesters/README.md` for deeper protocol and CLI details instead of copying those docs into workspace instructions.

---
applyTo: "ingesters/**/*.py,backend/tests/ingesters/**/*.py"
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
- Ingesters may import stable public interfaces from `src/`, such as normalized table containers, target-model metadata, and pure domain helpers.
- Ingesters may import `backend.app.ingesters.protocol` and `backend.app.ingesters.registry`, but should not import backend endpoints, routers, request or response models, or backend service-layer business logic.
- Prefer small stable interfaces from `src/` over deep imports into core internals. If an ingester needs broader reuse, extract or depend on a clearer core interface instead of reaching further into `backend/`.
- Keep external side effects at the ingester boundary or in injected collaborators; do not move file packaging, database writes, or service calls into `src/`.
- Architecture caveat: the protocol and registry currently live in `backend.app.ingesters`, so those imports are allowed as a temporary integration seam. Treat them as the only approved backend imports for ingesters unless the architecture is deliberately refactored.

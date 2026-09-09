# Shape Shifter – Ingesters (`ingesters/`) Agent Rules

Rules here apply when working in `ingesters/`. Also read the root `AGENTS.md` for cross-cutting rules.

## Structure

- Each ingester lives in its own directory: `ingesters/<name>/`.
- Implement the protocol defined in `backend/app/ingesters/protocol.py`.
- Register with `@Ingesters.register(key="<name>")` — discovery is automatic via `IngesterRegistry.discover()`.
- Do not add manual imports into `backend/app/ingesters/__init__.py` unless the existing system requires it.

## Implementation Rules

- Keep `validate()` and `ingest()` responsibilities strictly separate.
- Return structured result types from both methods — do not raise for domain-level failures.
- Put ingester-specific settings in `IngesterConfig.extra` — do not extend `IngesterConfig` for one-off fields.
- Use explicit `IngesterConfig` values in tests — do not rely on `ConfigValue` or `ConfigStore` in test code.

## Dependency Boundaries

- Ingesters may depend on stable public interfaces in `src/`, such as normalized table containers, target-model metadata, and pure domain helpers.
- Ingesters may depend on `backend.app.ingesters.protocol` and `backend.app.ingesters.registry` because those modules currently define the ingester integration surface.
- Ingesters must not depend on backend API endpoints, routers, request or response models, or backend service-layer business logic.
- Prefer small stable interfaces from `src/` over deep imports into core internals. If an ingester needs broader orchestration help, extract a reusable domain interface instead of reaching further into `backend/`.
- Keep external side effects at the ingester boundary or in injected collaborators. Do not move file packaging, database writes, or service calls into `src/`.

## Architecture Caveat

- The current ingester protocol and registry live under `backend.app.ingesters`, so ingesters are allowed to import those modules even though that is not a perfect layering outcome.
- Treat `backend.app.ingesters.protocol` and `backend.app.ingesters.registry` as the only approved backend imports for ingesters unless a broader architectural decision is made.
- Long term, if this coupling becomes painful, move the protocol and registry primitives into a neutral shared package rather than expanding ingester dependencies on backend services.

## References

- Protocol and CLI details: `backend/app/ingesters/README.md` and `ingesters/README.md`.
- Prompt template: `.github/prompts/add-loader.prompt.md` (closest analogue for data-reading ingesters).

## Testing

- Mock external services and file I/O — do not hit real databases or APIs in unit tests.
- Test `validate()` and `ingest()` independently with explicit config fixtures.
- Use `@pytest.mark.asyncio` if the ingester is async.

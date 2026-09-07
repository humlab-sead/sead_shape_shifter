---
description: "Use when editing Python code in src, backend, ingesters, or tests. Covers API/Core boundaries, dependency injection, validators, loaders, and test patterns."
applyTo: "src/**/*.py,backend/**/*.py,ingesters/**/*.py,tests/**/*.py"
---
# Python Architecture

- Use absolute imports only: `from src...` and `from backend.app...`.
- Keep API models in `backend/app/models/` and domain logic in `src/`.
- Preserve the service and router separation; keep business logic in services, not API route handlers.
- Convert API and Core models with mappers; resolve environment variables and directives only in the mapper layer.
- When transforming configuration data, do not mutate input objects; make deep copies before changing nested values.
- Prefer constructor injection or factory functions to break circular dependencies; use `TYPE_CHECKING` for type-only imports.
- Keep validators in `src/validators/` pure: accept data/config, return domain issues, and do not fetch data or import API DTOs.
- Register validators, loaders, filters, and ingesters through the existing registries.
- Define loader schemas on the loader class as `schema: ClassVar[DriverSchema]`; do not maintain separate schema files.
- Await loaders and check backend service sync/async boundaries before calling.
- Write docstrings using concrete behavior-first wording. Say what the function reads, returns, uses, or does not do. Prefer wording like `Reads sample rows from a CSV file.` and `Returns validation errors for missing required fields.` Avoid vague wording like `Ingests artifacts across the import boundary.`
- Backend feature checklist: update endpoint, models, service, and router registration.
- Preferred tests: `@pytest.mark.asyncio` for async code, `TestClient` for unprotected backend routes, the conftest `authorized_client` fixture (async, with `await` on every request) for routes protected by `require_project(...)`, `service.state = mock_state` for service tests, and patched connection/internal methods for loader tests. Register protected-route projects by creating them via `POST /api/v1/projects`, not by writing `shapeshifter.yml` to disk.

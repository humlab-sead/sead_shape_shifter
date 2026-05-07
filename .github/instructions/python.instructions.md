---
description: "Use when editing Python code in src, backend, ingesters, or tests. Covers API/Core boundaries, dependency injection, validators, loaders, and test patterns."
applyTo: "src/**/*.py,backend/**/*.py,ingesters/**/*.py,tests/**/*.py"
---
# Python Architecture

- Use absolute imports only: `from src...` and `from backend.app...`.
- Keep API models in `backend/app/models/` and domain logic in `src/`.
- Convert API and Core models with mappers; resolve environment variables and directives only in the mapper layer.
- Prefer constructor injection or factory functions to break circular dependencies; use `TYPE_CHECKING` for type-only imports.
- Keep validators in `src/validators/` pure: accept data/config, return domain issues, and do not fetch data or import API DTOs.
- Register validators, loaders, filters, and ingesters through the existing registries.
- Define loader schemas on the loader class as `schema: ClassVar[DriverSchema]`; do not maintain separate schema files.
- Await loaders and check backend service sync/async boundaries before calling.
- Backend feature checklist: update endpoint, models, service, and router registration.
- Preferred tests: `@pytest.mark.asyncio` for async code, `TestClient` for backend routes, `service.state = mock_state` for service tests, and patched connection/internal methods for loader tests.

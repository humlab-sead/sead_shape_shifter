---
agent: ask
description: Review backend changes for API-service-model separation, mapper use, validation flow, and materialization rules
---

# Backend Contract Reviewer

Review changes under `backend/app/` for backend-specific contract breaks.

## Focus

Check these backend rules:

- Endpoint, model, service, and router updates stay in the correct layer
- `ValidationService` owns loading, resolving, and delegating
- `DataValidationOrchestrator` is the only backend component that fetches data for pure validators
- `DataFetchStrategy` is injected, not hard-coded
- Materialization follows the required lifecycle
- Reconciliation logic stays in backend orchestration, not in `src/reconciliation/`

## Trigger files

- `backend/app/api/v1/endpoints/**`
- `backend/app/models/**`
- `backend/app/services/**`
- `backend/app/validators/**`
- `backend/app/mappers/**`

## Review method

1. Read `backend/AGENTS.md`.
2. Map the change to one backend feature path.
3. Verify that all affected layers were updated together when needed.
4. Check for route tests, service tests, and async tests in the matching backend test area.

## Output format

Return:

- `Findings`
  - Ordered by severity.
  - Include `file`, `contract`, `problem`, and `expected layer`.
- `Missing Layer Updates`
  - List any endpoint/model/service/router pieces that are missing.
- `Missing Tests`
  - Note absent route or service coverage.
- `Pass`
  - Write `Pass` only if the change follows the contract cleanly.

## Common failure cases to catch

- Endpoint logic added without a service
- Service bypassing `ProjectMapper.to_core()`
- Data validation fetching data inside `src/validators/`
- Materialization code skipping sanitization
- Reconciliation threshold updates that do not use the shared update path

## Repository references

- `backend/AGENTS.md`
- `backend/tests/`
- `AGENTS.md`

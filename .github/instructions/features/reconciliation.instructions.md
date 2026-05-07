---
applyTo: "src/reconciliation/**,backend/app/services/reconciliation*,backend/app/clients/reconciliation_client.py,backend/tests/test_reconciliation*"
---

# Reconciliation – AI Coding Instructions

## Domain / Backend Separation

- `src/reconciliation/` — pure domain models and strategy logic; no HTTP, no DB.
- `backend/app/services/reconciliation*` — backend orchestration with infrastructure.
- `backend/app/clients/reconciliation_client.py` — async `httpx` client wrapping OpenRefine API.

Never import `backend.*` from `src/reconciliation/`.

## Source Strategy (`src/reconciliation/source_strategy.py`)

`ReconciliationSourceStrategy.determine_strategy()` is a pure function — no I/O. Three strategies:

| `SourceStrategyType` | Condition | Data source |
|---------------------|-----------|-------------|
| `TARGET_ENTITY` | No source, or source == entity name | Entity preview data |
| `ANOTHER_ENTITY` | Source is a different entity name | Other entity's preview data |
| `SQL_QUERY` | Source is a `ResolutionSource(type="sql", ...)` | Custom SQL via data source |

- Use `determine_strategy()` to pick the strategy; do not hard-code strategy selection in callers.
- `ReconciliationDataProvider` is a `Protocol` — implement it in the backend layer, pass it to the strategy executor.

## Domain Models (`src/reconciliation/model.py`)

- `EntityResolutionMetadata` — per-entity reconciliation config with `auto_accept_threshold` (default `0.95`) and `review_threshold` (default `0.70`).
- `EntityResolutionSet` — container for mapping entries for one entity+field.
- `ResolvedEntityPair` — single source-value → target-id mapping with `confidence`, `notes`, `will_not_match`.
- `ResolutionSource` — custom SQL source config with `data_source`, `type`, `query`.

Never set thresholds above 1.0 or below 0.0. `auto_accept_threshold` must be ≥ `review_threshold`.

## Confidence Thresholds

- `confidence >= auto_accept_threshold` (0.95) → auto-accepted; no manual review needed.
- `review_threshold <= confidence < auto_accept_threshold` → requires review.
- `confidence < review_threshold` (0.70) → rejected / will_not_match.

Use `update_thresholds()` to change both values atomically — never set them independently without checking the ordering invariant.

## OpenRefine Client

- All methods are async (`httpx.AsyncClient` with lazy singleton).
- Call `await client.close()` in teardown.
- Do not re-initialise the client per request — use the shared singleton.

## Common Mistakes

- Importing `httpx` or `backend.*` inside `src/reconciliation/` — domain stays pure.
- Hard-coding strategy type instead of calling `determine_strategy()`.
- Setting `auto_accept_threshold` < `review_threshold` — always validate ordering.
- Setting `will_not_match = True` on an entry that has a resolved `target_id` — semantically contradictory.
- Creating a new `httpx.AsyncClient` per request in the reconciliation client.

## Testing Expectations

- Test `determine_strategy()` with each of the three source conditions.
- Test threshold update: valid update, invalid ordering (should raise or clamp).
- Mock `ReconciliationDataProvider` when testing strategy executors.
- Use `pytest.mark.asyncio` for all client and backend service tests.

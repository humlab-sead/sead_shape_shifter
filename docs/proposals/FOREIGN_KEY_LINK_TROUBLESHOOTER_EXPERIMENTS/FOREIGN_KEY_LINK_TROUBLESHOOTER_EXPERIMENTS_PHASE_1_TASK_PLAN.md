# Foreign-Key Link Troubleshooter Experiments — Phase 1 Task Plan

## Phase Summary

**Phase:** 1 — Fixed-Input Snapshot Context. Source: [approved proposal](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS.md) and [phase plan, Phase 1](./FOREIGN_KEY_LINK_TROUBLESHOOTER_EXPERIMENTS_PHASE_PLAN.md#phase-1-fixed-input-snapshot-context).

**Status: Complete.** Implemented and validated on 2026-11-07; every `PH1-AC-*` criterion is covered by tasks `T1.1`–`T3.2` and passing validation `V-1`–`V-4`, recorded in [Implementation Evidence](#implementation-evidence). The budget is configurable with a 100 MiB default, and the per-computation peak rule below is approved.

The phase retains one reproduced warning's A/B frames, resolved configuration, and baseline diagnostic state for a fixed 15 minutes. A separate concurrent-admission cap is deferred. The client-side automatic reopen and refreshed-baseline notice belong to Phase 3; this phase must return an explicit expired-context outcome and support a fresh open.

**Phase acceptance criteria**

1. [x] `PH1-AC-1` (from `P-AC-1`): Open only after reproduction; inputs and original configuration remain fixed until expiry.
2. [x] `PH1-AC-2` (from `P-AC-10`): A failed, incomplete, or skipped configured-key diagnostic still permits opening, with no complete baseline totals or groups.
3. [x] `PH1-AC-3` (from `P-AC-7`): Every operation checks current user/project read access and ownership; expired inputs cannot be used and abandoned contexts are removed.
4. [x] `PH1-AC-4` (from `P-AC-7`): Reject retained inputs or projected peak allocation above the configured limit (100 MiB by default) before joining, with `ProjectedBudgetExceeded` and no complete metrics.

## Repository Findings

**Repository basis:** `feature/foreign-key-link-troubleshooter-experiments` at `01095086`, inspected 2026-11-07. Uncommitted changes to the approved proposal, proposal index, and phase plan were included as planning inputs; no implementation changes were present in the worktree status.

| Evidence | Verified current behavior | Planning implication |
|---|---|---|
| `backend/app/services/link_baseline_service.py::LinkBaselineService.build_baseline`, `_link` | Reproduces the selected warning with an isolated replay, keeps copied pre-link A and processed B frames in `LinkBaselineResult`, and checks the warning before returning reproduced status. | Reuse reproduction, FK identity, and resolved inputs; do not retain joined output or weaken eligibility. Budget the selected-link merge before `_link` materializes it. |
| `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService.run` | Rebuilds the baseline, runs configured-key diagnostics, and then runs or reuses the requested trial for every stateless request. Already detects configured-count mismatches and missing context. | Split context opening from later trial use; retain baseline status even when configured diagnostics fail. Preserve the existing stateless route until the planned contract cutover. |
| `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`, `_estimate_output_rows` | Preflight estimates production and diagnostic **row counts** with coerced key dtypes and the production null-match policy, then checks `LINK_TRIAL_MAX_OUTPUT_ROWS` before copying A/B and merging; it does not estimate bytes. | Reuse these counts rather than a second `groupby` estimate; cover diagnostic joins as well as production joins, and retain the independent row guard. |
| `src/transforms/link.py::ForeignKeyLinker.link_foreign_key`; `src/transforms/utility.py::merge_with_nonmatching_null_keys` | Production merges use separate `left_on`/`right_on` keys, selected/renamed remote columns, optional null-key separation, and intermediate frames. | The suggested shared-key merge estimate is a starting point, not a drop-in: use actual selected remote payload, include temporary columns and copies, and preserve distinct key and null behavior. |
| `backend/app/mappers/link_troubleshooter_mapper.py::LinkTroubleshooterMapper._map_baseline` | Sends reproduction row counts even if configured-key diagnostic status is failed or incomplete. | The new context response must represent an incomplete baseline without complete totals/groups; avoid an accidental change to the old stateless response before cutover. |
| `backend/app/api/v1/endpoints/link_troubleshooter.py::run_link_troubleshooter`, `get_link_troubleshooter_service`; `backend/app/authorization/dependencies.py::require_project` | The current route has project `Action.READ` protection but creates its coordinating service per request. `AuthorizedResource` carries the principal and project locator. | A context store must outlive a service instance; every context operation needs route authorization **and** matching stored principal/project identity. |
| `backend/app/core/state_manager.py::ApplicationState.start`, `_cleanup_stale_sessions`; `backend/app/main.py::lifespan` | In-process state and periodic cleanup have a lifespan-managed pattern; the application stops state on shutdown. | Use a shared lifespan-managed context store with expiry checks on access and periodic cleanup; do not piggyback on editing-session TTL. |
| `backend/app/core/config.py::Settings.LINK_TRIAL_MAX_OUTPUT_ROWS`; `backend/tests/test_config.py`; `backend/app/utils/error_handlers.py::handle_endpoint_errors` | The existing row cap defaults to 1,000,000, with default/override/invalid-value tests; an unhandled domain exception maps to a 500. | Add a separate configurable 100 MiB memory limit with the same settings test pattern, and map the projected-budget exception to an explicit, non-success API failure without exposing frame values. |
| `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/services/test_link_baseline_service.py`, `backend/tests/services/test_link_trial_service.py`, `backend/tests/api/v1/test_link_troubleshooter.py` | Existing tests cover reproduction, incomplete diagnostics, output-row limits, cache immutability, route authorization, and concealed 404s. | Extend these suites with clock-controlled snapshot, budget, expiry, and ownership cases; use the protected-route `authorized_client` fixture. |

## Scope

**In scope:** Backend context storage, 15-minute non-sliding TTL, periodic/on-access expiry, best-effort close, input and peak budget checks, incomplete-baseline representation for the new context, project/user checks, and additive context access needed by later phases.

**Out of scope:** Browser auto-reopen/notice, reset, new trial controls, exception groups and local paging, request-contract cutover, a concurrent-admission cap, persistent contexts, changes to production normalization or saved projects, and the integrity inspector. Phase 2 owns the full new trial/response contract; Phase 3 owns client refresh behavior and documentation cutover.

**Affected components:** `backend/app/services/`, `backend/app/models/`, `backend/app/api/v1/endpoints/`, `backend/app/mappers/`, settings, API error mapping, application lifespan, backend tests, and runtime-configuration documentation. The existing stateless route remains available while the new contract is assembled.

## Work Breakdown

All areas are ready for implementation. Proposed new files are marked `NEW`; proposed context operations are not existing APIs.

### Area 1: Retain and expire reproduced snapshots

**Objective:** An authorized caller can retain one fixed set of reproduced inputs for 15 minutes and release it on Close or expiry.

**Affected code:** `backend/app/services/link_baseline_service.py::LinkBaselineResult`, `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`, `backend/app/main.py::lifespan`, `backend/app/services/link_experiment_context_store.py` (**NEW**), `backend/tests/services/test_link_experiment_context_store.py` (**NEW**).

**Dependencies:** Approved proposal and Phase 1 readiness in the source phase plan (both satisfied).

**Tasks:**

- [x] `T1.1` **Change:** Retain only reproduced baseline inputs and original resolved settings in an opaque, user/project-owned snapshot.
  - **Target:** `backend/app/services/link_experiment_context_store.py` (**NEW**) and `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`.
  - **Current → required:** A/B and resolved project live for one request → the shared store keeps them unchanged until fixed expiry; ineligible or non-reproduced warnings cannot create a usable context.
  - **Implementation:** Store the `LinkBaselineResult` inputs, original FK identity, owner principal ID, project locator, baseline diagnostic state, and creation/expiry time. Return only an opaque identifier and serializable baseline details, never the frames or resolved project. Keep the store shared across request-scoped service instances.
  - **Constraints:** Do not write to saved projects, production caches, or logs containing row values. Preserve the existing stateless endpoint until Phase 3.
  - **Validation:** `V-1`, `V-3`; use the existing reproduced, changed-warning, and cache-immutability cases plus a `NEW` frozen-input/source-change test.

- [x] `T1.2` **Change:** Expire snapshots after 15 minutes even when the dialog is abandoned.
  - **Target:** `backend/app/services/link_experiment_context_store.py` (**NEW**) and `backend/app/main.py::lifespan`.
  - **Current → required:** No cross-request state or expiry → on-access checks deny expired IDs; a lifespan-managed periodic sweep removes unaccessed expired records; Close removes a record best-effort.
  - **Implementation:** Use a testable clock and synchronization around lookup/removal. Stop cleanup on shutdown. A computation that already holds a snapshot may finish, but later lookup cannot reuse the expired context; release its remaining references afterward.
  - **Constraints:** TTL is non-sliding; an expired response does not itself rerun reproduction or a submitted trial. Phase 3 owns transparent client reopen.
  - **Validation:** `V-1`, `V-2`; test just before/at expiry, repeated Close, abandoned-dialog sweep, and in-flight cleanup without exposing frames.

**Completion evidence:** A reproduced context stays stable before expiry, and expiry/Close remove it without touching other application state.

### Area 2: Preserve incomplete diagnostics and enforce the budget

**Objective:** Context opening reports the configured diagnostic honestly, and merges exceeding the configured budget fail before materialization.

**Affected code:** `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`, `backend/app/services/link_baseline_service.py::LinkBaselineService._link`, `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`, `_estimate_output_rows`, `backend/app/mappers/link_troubleshooter_mapper.py::LinkTroubleshooterMapper`, `backend/app/core/config.py::Settings`, `backend/app/exceptions.py`, `backend/app/utils/error_handlers.py`, `backend/tests/test_config.py`, `docs/OPERATIONS.md`, existing service/mapper tests.

**Dependencies:** Area 1; the configured budget and peak rule in the source phase plan are approved.

**Tasks:**

- [x] `T2.1` **Change:** Keep a context when warning reproduction succeeds but configured-key diagnostics do not complete.
  - **Target:** `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`, `backend/app/mappers/link_troubleshooter_mapper.py::LinkTroubleshooterMapper`, `backend/app/models/link_troubleshooter.py`.
  - **Current → required:** Failed/incomplete configured diagnostics already return a status, but `_map_baseline` can include reproduction counts → new context baseline status is explicit and has no complete totals or exception groups; trials remain possible in a later phase.
  - **Implementation:** Separate reproduced-warning status from diagnostic completeness. Retain the original inputs and store failed, incomplete, or not-run diagnostic status without inventing calculated totals. Keep the existing stateless mapper contract until cutover.
  - **Constraints:** A failure to reproduce the warning still prevents opening. Do not equate diagnostic budget failure with an eligible baseline failure.
  - **Validation:** `V-1`, `V-3`; exercise failed, row-limited, and skipped configured diagnostics and count-mismatch cases.

- [x] `T2.2` **Change:** Reject over-budget inputs and projected selected-link joins before allocating their output.
  - **Target:** `backend/app/core/config.py::Settings`, `backend/app/services/link_baseline_service.py::LinkBaselineService._link`, `backend/app/services/link_trial_service.py::LinkTrialService.run_trial`, `_estimate_output_rows`, `backend/app/exceptions.py`, `backend/app/utils/error_handlers.py`, `backend/tests/test_config.py`, `docs/OPERATIONS.md`.
  - **Current → required:** Only a trial row-count preflight exists → retained-frame bytes and projected peak bytes for copies, production AB, and diagnostic AB are checked separately from row counts before their merges.
  - **Implementation:** Add `Settings.LINK_EXPERIMENT_MAX_MEMORY_MB: int = Field(default=100, ge=1)` (environment override `SHAPE_SHIFTER_LINK_EXPERIMENT_MAX_MEMORY_MB`); compare against `limit * 1024 * 1024` bytes. Check `A.memory_usage(index=False, deep=True).sum() + B.memory_usage(index=False, deep=True).sum()` before retaining inputs or making merge copies. Reuse `_estimate_output_rows` for inner/left production and left diagnostic cardinalities, including dtype coercion and null behavior; the suggested `groupby(..., dropna=False)` formula would count forbidden null matches and assumes identical key names. Measure per-row widths from the actual A frame and selected/renamed remote columns (system ID, keys, extras); count both key sides when names differ, and include merge indicator, diagnostic positions, and null-key temporaries in their corresponding projected widths. For empty frames, use at least 64 bytes per projected column in place of dividing by zero; retain left-join unmatched rows. For each stage, project `retained A/B bytes + 4 * (A/B input bytes) + 3 * (estimated output rows * estimated output row width)`; take the larger production/diagnostic projection since their joins run sequentially. Run each stage's check before its merge, including reproduction, and reject on `>` (allow equality). Raise `ProjectedBudgetExceeded` with no partial metrics or row values; a rejected configured-key diagnostic after reproduced warning leaves an explicitly incomplete baseline, while over-budget retained input or reproduction cannot open a context.
  - **Constraints:** The factors provide headroom for observed copies and pandas merge intermediates but are not a strict peak-memory guarantee, particularly for uneven variable-width rows. Document the setting, units, default, and per-computation limitation in `docs/OPERATIONS.md`. Preserve the independent row limit and production linker/constraint behavior; no concurrent-admission cap in this phase.
  - **Validation:** `V-2`, `V-3`; test equality and one byte over the configured limit (default and override), empty input sides, wide/variable-width rows, duplicate-key expansion, distinct key names, null-match prevention, diagnostic-only overage, and no merge on rejection.

**Completion evidence:** An eligible warning opens with either complete or explicitly incomplete diagnostics; selected over-budget merges do not run.

### Area 3: Authorize context operations and verify the contract

**Objective:** The backend exposes the Phase 1 context lifecycle without letting an ID cross users or projects.

**Affected code:** `backend/app/api/v1/endpoints/link_troubleshooter.py::run_link_troubleshooter`, `get_link_troubleshooter_service`, `backend/app/models/link_troubleshooter.py`, `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`, `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/services/test_link_troubleshooter_service.py`.

**Dependencies:** Areas 1–2. Preserve existing route behavior until the Phase 3 cutover.

**Tasks:**

- [x] `T3.1` **Change:** Add context-open, access, and Close operations under the existing protected link-troubleshooter router.
  - **Target:** `backend/app/api/v1/endpoints/link_troubleshooter.py`, `backend/app/models/link_troubleshooter.py`, `backend/app/services/link_troubleshooter_service.py::LinkTroubleshooterService`.
  - **Current → required:** The registered router has one stateless POST and each dependency call creates a service → additive context operations use a shared store and return identifier, baseline status, and explicit expired/unavailable outcomes.
  - **Implementation:** Use `require_project(Action.READ)` for each operation, then compare `authorized_project.principal.principal_id` and the authorized project locator with the stored owner before access or Close. An opaque ID alone grants nothing. Return a concealed failure for mismatches; do not silently create a replacement context when expired.
  - **Constraints:** The exact new route shapes must be coordinated with Phase 2's trial contract; do not remove paging fields or change the legacy stateless caller in Phase 1.
  - **Validation:** `V-2`, `V-3`; test other user, other project, revoked read access, missing/expired ID, and successful Close using the existing `authorized_client` pattern.

- [x] `T3.2` **Change:** Cover the context lifecycle and preservation paths with service and protected-route tests.
  - **Target:** `backend/tests/services/test_link_experiment_context_store.py` (**NEW**), `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/services/test_link_baseline_service.py`, `backend/tests/services/test_link_trial_service.py`, `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/test_config.py`.
  - **Current → required:** Stateless behavior is tested → snapshot creation, fixed inputs, incomplete diagnostics, budget rejection, expiry, cleanup, and ownership are tested without losing existing reproduction or row-cap coverage.
  - **Implementation:** Use fixed or injectable time, representative narrow/wide A/B frames, mock `ProjectService`/`ShapeShifter` where appropriate, and create protected-route projects through the API. Assert no replay for in-TTL access and no complete metrics for failed diagnostics or budget errors.
  - **Constraints:** Do not rewrite tests for Phase 2 controls or Phase 3 browser behavior in this phase.
  - **Validation:** `V-1`, `V-2`, `V-3`, `V-4`.

**Completion evidence:** All context operations check current authorization and owner identity, and the original stateless route still passes its existing tests.

## Acceptance-Criteria Coverage

| Criterion | Source | Task IDs | Validation IDs | Expected evidence |
|---|---|---|---|---|
| `PH1-AC-1` | `P-AC-1` | `T1.1`, `T3.1`, `T3.2` | `V-1`, `V-3` | Reproduced warning alone opens; unchanged A/B and settings reused until TTL, with no replay on access. |
| `PH1-AC-2` | `P-AC-10` | `T1.1`, `T2.1`, `T3.2` | `V-1`, `V-3` | Failed/incomplete/not-run diagnostic opens with no complete totals/groups. |
| `PH1-AC-3` | `P-AC-7` | `T1.1`, `T1.2`, `T3.1`, `T3.2` | `V-1`, `V-2`, `V-3` | Cross-user/project and revoked access denied; expired and abandoned contexts removed. |
| `PH1-AC-4` | `P-AC-7` | `T2.2`, `T3.2` | `V-2`, `V-3` | Configurable 100 MiB default and override, input/peak checks at and above threshold; overage reports `ProjectedBudgetExceeded` before merge. |

## Validation And Testing

The repository's `Makefile` defines `make sync` (`uv sync --extra all`) and `make backend-test`; `pyproject.toml` provides the `all` extra with API and dev dependencies. The baseline attempt failed before collection because `.venv/` had neither `pytest` nor `fastapi`; `uv sync --extra all` restored them before any check below ran.

| ID | Check and target | Command or method | Covers | Expected result | Baseline |
|---|---|---|---|---|---|
| `V-1` | Service and context-store checks in `backend/tests/services/test_link_experiment_context_store.py` (**NEW**), `test_link_baseline_service.py`, `test_link_troubleshooter_service.py` | `uv run pytest backend/tests/services/test_link_experiment_context_store.py backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_troubleshooter_service.py -q -n 0` after `make sync` | `PH1-AC-1`–`PH1-AC-3` | Snapshot fixed through 15 minutes, expiry/cleanup and incomplete baseline explicit; existing reproduction tests pass. | Pass: part of the 144-test focused run recorded in Implementation Evidence. |
| `V-2` | Budget, cleanup, and owner checks in `backend/tests/test_config.py`, `backend/tests/services/test_link_experiment_context_store.py` (**NEW**), `test_link_trial_service.py`, and `backend/tests/api/v1/test_link_troubleshooter.py` | `uv run pytest backend/tests/test_config.py backend/tests/services/test_link_experiment_context_store.py backend/tests/services/test_link_trial_service.py backend/tests/api/v1/test_link_troubleshooter.py -q -n 0` after `make sync` | `PH1-AC-3`, `PH1-AC-4` | Default 100 MiB, environment override, and invalid settings validated; exact-limit allowed and over-limit rejected before merge; distinct/compound keys, forbidden null matches, empty sides, wide rows, diagnostic-only overage, concealed cross-user/project errors, revoked read access, and in-flight cleanup covered. | Pass: part of the 144-test focused run recorded in Implementation Evidence. |
| `V-3` | Existing focused regression suites and Phase 1 additions | `uv run pytest backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_trial_service.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/api/v1/test_link_troubleshooter.py -q -n 0` after `make sync` | All `PH1-AC-*`; preserve current caller behavior | Existing stateless route, authorization, reproduction, and row-limit tests pass together with new cases. | Pass, with two unrelated route-inventory failures that also fail at `01095086`; see Implementation Evidence. |
| `V-4` | Python quality checks for touched backend code/tests | `uv run ruff check backend/app/services/link_experiment_context_store.py backend/app/services/link_baseline_service.py backend/app/services/link_trial_service.py backend/app/services/link_troubleshooter_service.py backend/app/api/v1/endpoints/link_troubleshooter.py backend/app/models/link_troubleshooter.py backend/tests/services/test_link_experiment_context_store.py backend/tests/test_config.py`; `uv run pyright --threads 2 backend/app` | All work areas | No new lint or type errors in affected backend code. | Pass: `ruff` reported `All checks passed!` and `pyright` reported `0 errors, 0 warnings, 0 informations`. |

## Implementation Evidence

Recorded 2026-11-07 on `feature/foreign-key-link-troubleshooter-experiments` at `01095086`. The plan's uncommitted proposal documents were preserved unchanged.

- Environment: `uv sync --extra all` restored `pytest`, `pytest-asyncio`, `pytest-xdist`, `fastapi`, and `ruff` in `.venv/`. The blocking environment gap is resolved.
- `V-1`: `uv run pytest backend/tests/services/test_link_experiment_context_store.py backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_troubleshooter_service.py -q -n 0`. Result: 78 passed, exit 0.
- `V-2`: `uv run pytest backend/tests/test_config.py backend/tests/services/test_link_experiment_context_store.py backend/tests/services/test_link_trial_service.py backend/tests/api/v1/test_link_troubleshooter.py -q -n 0`. Result: 88 passed, exit 0.
- `V-3`: `uv run pytest backend/tests/services/test_link_baseline_service.py backend/tests/services/test_link_trial_service.py backend/tests/services/test_link_troubleshooter_service.py backend/tests/api/v1/test_link_troubleshooter.py -q -n 0`. Result: 107 passed, exit 0. One focused command over all six affected suites collected and passed 144 tests.
- `V-4` commands: `.venv/bin/python -m ruff check backend/app backend/tests` returned `All checks passed!`; `uv run pyright --threads 2 backend/app` returned `0 errors, 0 warnings, 0 informations`; `uv run isort --check-only` and `uv run black --check` are clean on the touched files.
- `V-3` wider run: `.venv/bin/python -m pytest backend/tests -q -n 4`. Four modules fail outside this phase and none are caused by these changes.
  - `backend/tests/authorization/test_route_authentication.py::test_route_inventory_matches_assembled_api_routes` and `::test_route_inventory_matches_authorization_metadata` fail on `POST /api/v1/projects/{project_name}/integrity-troubleshooter`, which exists at `01095086` but has no entry in `docs/AUTHORIZATION_ROUTE_INVENTORY.md` at that commit. The three routes added by this phase do match their authorization metadata.
  - `backend/tests/data_providers/arbodat/test_project_mapper_integration.py`, `test_validation.py`, and `test_workflow.py` fail or abort because `data/projects/arbodat/shapeshifter.yml` and the Access fixture are absent from this environment.
- New coverage: 22 cases in `backend/tests/services/test_link_experiment_context_store.py`; 9 context lifecycle cases, 3 memory-budget cases, 2 reproduction-budget cases, 11 protected-route cases, and 4 settings cases in the existing suites.
- Deliberate addition outside the listed deliverables: three rows in `docs/AUTHORIZATION_ROUTE_INVENTORY.md`. The assembled-route test requires every protected route to be documented, so a new protected route cannot ship without them.
- Recorded request contract for later phases: `POST /api/v1/projects/{project_name}/link-experiment-contexts` opens a context, `GET .../link-experiment-contexts/{context_id}` reads the retained baseline, and `DELETE .../link-experiment-contexts/{context_id}` releases it. Expiry answers `410` with `reason=context_expired`; unknown or foreign identifiers answer a concealed `404`.

## Deliverables

| Deliverable | Target | Task IDs | Completion evidence |
|---|---|---|---|
| Shared expiring context | `backend/app/services/link_experiment_context_store.py` (**NEW**), `backend/app/main.py::lifespan` | `T1.1`, `T1.2` | Fixed snapshot, expiry, sweep, and Close verified. |
| Baseline and budget guards | `backend/app/services/link_baseline_service.py`, `backend/app/services/link_trial_service.py`, `backend/app/services/link_troubleshooter_service.py`, `backend/app/core/config.py`, `backend/app/exceptions.py`, `backend/app/utils/error_handlers.py`, `docs/OPERATIONS.md` | `T2.1`, `T2.2` | Configurable 100 MiB default documented; no over-budget merge or success-shaped incomplete result. |
| Context API and mapping | `backend/app/api/v1/endpoints/link_troubleshooter.py`, `backend/app/models/link_troubleshooter.py`, `backend/app/mappers/link_troubleshooter_mapper.py` | `T2.1`, `T3.1` | Protected, owner-scoped operations and accurate baseline status. |
| Focused tests | `backend/tests/services/test_link_experiment_context_store.py` (**NEW**), `backend/tests/services/test_link_baseline_service.py`, `backend/tests/services/test_link_trial_service.py`, `backend/tests/services/test_link_troubleshooter_service.py`, `backend/tests/api/v1/test_link_troubleshooter.py`, `backend/tests/test_config.py` | `T3.2` | `V-1`–`V-3` pass once dependencies are available. |

## Progress Tracker

| Area | Status | Dependencies | Notes |
|---|---|---|---|
| Area 1: Snapshot context | Done | None | Preserve the existing stateless route. |
| Area 2: Diagnostic and budget | Done | Area 1 | Approved budget rule applied; row cap left independent. |
| Area 3: Context API and tests | Done | Areas 1–2 | Stateless route unchanged; three protected context routes added. |

## Definition Of Done

- [x] Implement the approved input/copy/production-join/diagnostic-join estimation rule and configurable budget.
- [x] Every `PH1-AC-*` criterion has passing task and validation evidence (`V-1`–`V-4`).
- [x] All three areas and listed deliverables are complete; the existing stateless caller still works.
- [x] Auth, TTL boundary, abandoned-context cleanup, incomplete baseline, and projected-budget failure tests pass.
- [x] Existing reproduction, join-row-limit, saved-project immutability, and cache-preservation behavior is regression-tested.
- [x] API models, error mapping, service lifecycle, and tests are consistent; any deviation and follow-up are documented.
- [x] No unresolved decision affects implementation, correctness, or validation. If source behavior differs from the verified findings, stop and report it rather than broadening the phase.

## Risks And Open Questions

- **Estimate limitation:** The suggested merge formula estimates result bytes, not peak allocation, and assumes shared keys and nonempty inputs. The approved copy/output multipliers and empty-side width avoid those assumptions, but pandas memory usage and concurrent work can still exceed projections. Measure actual memory if worker limits change; do not present this as a strict peak guarantee.
- **Known limitation:** Per-computation checks do not cap combined memory from simultaneous operations; concurrent admission was explicitly deferred by the approved proposal. Do not describe this phase as a process-wide memory guarantee.
- **Validation environment:** `.venv/` now has `pytest` and `fastapi` after `uv sync --extra all`, so `V-1`–`V-4` ran. One pre-existing gap remains outside this phase: three `data_providers/arbodat` modules need test data that this environment does not include. It does not affect this phase's deliverables. The other gap noted at implementation time, the missing `POST /api/v1/projects/{project_name}/integrity-troubleshooter` route-inventory row, was closed during Phase 2.

# Proposal: Sead Change Request Ingester Readability Refactor

## Status

- Working refactor plan
- Scope: `ingesters/sead_change_request/ingester.py`
- Goal: reduce class size, remove mixed abstraction levels, and make the protocol adapter easier to read and review
- Current branch progress:
	- input resolution extracted to `input_resolution.py`
	- artifact bundle writing extracted to `artifact_writer.py`
	- validation and ingestion result assembly extracted to `result_builders.py`
	- bundle-planning orchestration moved into `planning.py`
- Current decision: stop here; the adapter is now readable enough without more local extraction

## Summary

`SeadChangeRequestIngester` currently does too many jobs.

It resolves inputs, parses config, plans tables, formats validation output, controls ingestion flow, writes artifact bundles, and translates failures into result objects.

The class works, but it is hard to scan because those responsibilities are mixed together.

The refactor should make the ingester class a thin protocol adapter. Most helper logic should move into focused modules.

## Problem

The main readability problem is not the number of helper methods by itself.

The real problem is that helpers from different abstraction levels live in the same class:

- input and config resolution
- submission-context parsing and normalization
- table planning orchestration
- validation and ingestion result formatting
- file-system bundle writing
- protocol-facing control flow

That makes the class longer than it needs to be and forces the reader to switch mental context too often.

## Scope

This plan covers:

- refactoring `SeadChangeRequestIngester` into a smaller adapter
- moving input-resolution logic into a dedicated module
- moving artifact writing into a dedicated module
- moving validation and ingestion result assembly into focused helpers
- simplifying submission-context parsing into one cohesive parser

## Non-Goals

- changing planning, identity, materialization, collision-check, or SQL-rendering behavior
- redesigning the shared preparation flow in `preparation.py`
- changing public ingester protocol types beyond what is required for readability
- broad refactoring outside `ingesters/sead_change_request` unless a dependency forces a small adjacent change

## Proposed Design

### 1. Restore a green baseline first

Do not start the readability refactor while the current branch still has unrelated breakage.

Fix the current import and test inconsistencies first so the refactor can be reviewed as a behavior-preserving change.

### 2. Extract input resolution into its own module

Move the whole input/config parsing block out of `SeadChangeRequestIngester` into a module such as `input_resolution.py`.

Move these responsibilities together:

- source bundle loading and workbook reading
- target-model resolution
- submission-context parsing and normalization
- identity-assignment parsing
- deploy-strategy resolution
- input-related exceptions if they remain package-specific

Recommended shape:

- `resolve_inputs(config, source) -> ResolvedInputs`, or
- `SeadChangeRequestInputResolver.resolve(source) -> ResolvedInputs`

### 3. Extract artifact writing into its own module

Move bundle emission out of the ingester into a small writer module such as `artifact_writer.py`.

Move:

- artifact directory naming
- directory creation and cleanup
- SQL file writing
- manifest writing
- sidecar file emission

Recommended shape:

- `write_artifact_bundle(output_folder, submission_context, deploy_artifact) -> Path`

### 4. Extract validation and ingestion result builders

Keep `validate()` and `ingest()` in the ingester, but move detail-heavy result assembly into coarser helpers.

Recommended helpers:

- `build_validation_result(preparation) -> ValidationResult`
- `build_validation_infos(preparation) -> list[str]`
- `check_ingestion_preconditions(preparation) -> IngestionResult | None`

The goal is to make `validate()` and `ingest()` read like short phase pipelines instead of long mixed control-flow blocks.

### 5. Collapse submission-context parsing into one parser

The current submission-context logic is correct but visually noisy because it is split across several tiny methods.

Replace that helper cluster with one focused parser such as:

- `parse_submission_context(data, default_submission_name) -> SubmissionContext`

This parser should own:

- optional string extraction
- timestamp parsing
- datatype normalization
- identifier normalization
- description normalization

### 6. Move input-specific errors next to input resolution

The current error hierarchy is closely tied to input parsing.

If input resolution moves out of the ingester, these types should likely move with it:

- `InputResolutionError`
- `SourceBundleError`
- `TargetModelError`
- `SubmissionContextError`
- `IdentityAssignmentError`
- `DeployStrategyError`

### 7. Keep the existing domain modules in place

Do not reopen boundaries that already make sense.

Leave these modules where they are unless the refactor exposes a concrete mismatch:

- `planning.py`
- `preparation.py`
- `package_builder.py`
- `sql_builder.py`
- `identity_resolution.py`
- `materialization.py`
- `collision_checks.py`

## Target End State

After the refactor, `SeadChangeRequestIngester` should mainly contain:

- `__init__`
- `get_metadata()`
- `validate()`
- `ingest()`
- one shared `_prepare_change_request()` helper, if still useful

The rest should live in focused modules.

## Delivery Order

1. Completed: fix the broken baseline and stale test expectations.
2. Completed: extract input resolution.
3. Completed: extract artifact writing.
4. Completed: extract validation and ingestion result builders.
5. Completed: move bundle-planning orchestration out of the ingester.
6. Completed: run the focused ingester test file after each slice.
7. Completed: run the full ingester test slice.
8. Completed: stop here; the remaining ingester-local flow is small enough to keep in the adapter.

## Validation And Acceptance Criteria

The refactor is complete when:

- `SeadChangeRequestIngester` is visibly shorter and mostly protocol-facing
- input resolution no longer lives inside the ingester class
- artifact writing no longer lives inside the ingester class
- `validate()` and `ingest()` read as short phase pipelines
- behavior stays unchanged for planning, identity, materialization, collision checks, and artifact rendering

Recommended validation sequence:

- `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q`
- `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_sql_builder.py -q`
- `PYTHONPATH=.:backend pytest backend/tests/ingesters/test_sead_change_request_confirmation.py -q` if confirmation compatibility remains
- `PYTHONPATH=.:backend pytest backend/tests/ingesters -q`

Current branch validation completed:

- `./.venv/bin/pytest backend/tests/ingesters/test_sead_change_request_ingester.py -q`
- `./.venv/bin/pytest backend/tests/ingesters -q`

## Final Recommendation

Stop the refactor at the current boundary.

The main readability goals are already met:

- `SeadChangeRequestIngester` is now a much thinner protocol adapter
- input resolution, artifact writing, result assembly, and bundle planning already live in focused helpers
- the remaining local control flow is small enough that moving more code would likely add indirection without a comparable readability gain

Treat any further extraction as a separate follow-up only if a new concrete readability problem appears.
# Direct Target-Id Foreign Keys — Phase Plan

Source: [Direct Target-Id Foreign Keys](DIRECT_TARGET_ID_FOREIGN_KEYS.md).

## Summary

Deliver direct target-ID FKs in three phases: establish the project declaration and conformance rules, validate and package supplied IDs in the change-request ingester, then connect saved-project callers and verify the complete flow. The default `system_id` path remains in use when no direct-ID declaration is present.

## Problem

A source may already supply a target ID, yet the current change-request path needs a referenced project entity to translate a local `system_id`. The proposal allows an explicit per-project exception for direct target-model FKs while requiring a target database check before those IDs enter a package.

## Scope

This plan covers project configuration, Core and API preservation of the declaration, conformance, the change-request ingester, saved-project integration, documentation, regression checks, and a representative pilot. It excludes non-integer target IDs, `via` and bridge FKs, IDs for rows created in the same change request, and changes to existing Core FK links.

## Current Position

- Core FK links put a referenced entity's local `system_id` in the column named by its `public_id`. The project has no `foreign_key_value_sources` declaration today.
- Conformance checks direct FKs, induced entities, globally required entities, and no-orphan-facts separately. A direct-ID declaration must be handled consistently across them.
- Change-request projection currently translates FK values through a referenced resolved table. The target database checker is optional, and the table-based validation path does not yet require a target-ID lookup.
- The [proposal](DIRECT_TARGET_ID_FOREIGN_KEYS.md) fixes the declaration, allowed values, database validation rule, and default behavior. Its planning handoff records no blocking design question.

## Phase Plan

### Phase 1: Project declaration and conformance

**Goal**

Accept an explicit FK value source and report what can be checked before change-request validation.

**Focus**

- Preserve `foreign_key_value_sources` through the API and Core project model without creating a Core link or dependency for `public_id` mode.
- Reject invalid declarations with distinct machine-readable codes; apply direct-ID conformance across all relevant relationship checks.
- Expose the declaration in the editor schema while retaining the scaffold's `system_id` default.

**Depends On**

- The proposal's fixed project-level declaration and direct-FK eligibility rules.

**Outputs**

- A resolved project declaration and conformance result that the ingester and saved-project caller can use.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) API and Core project representations preserve declared `system_id` and `public_id` sources. A `public_id` declaration creates no Core FK link or dependency; omission and `system_id` retain current linking behavior.
- `PH1-AC-2` (from `P-AC-2`) Unknown sources or relationships, missing target metadata, `via` FKs, and conflicting Core links fail with distinct machine-readable direct-mode codes.
- `PH1-AC-3` (from `P-AC-3`) A valid direct-ID FK may omit an otherwise optional referenced project entity and link. Conformance reports the pending database check without false direct-FK, induced-entity, or no-orphan-facts errors; globally required entities remain required.
- `PH1-AC-4` (from `P-AC-9`) The API project model and editor schema accept the declaration, and the default scaffold still produces local-ID links.
- `PH1-AC-5` (from `P-AC-8`) Existing `system_id` project conformance results and default-path diagnostics remain unchanged against the recorded baseline.

**Validation Milestones**

- `VM-1` (`PH1-AC-1`–`PH1-AC-5`): configuration and conformance cases distinguish valid, invalid, direct, and default paths; the pre-existing standard-model failures are recorded before comparison.

**Task-Plan Handoff**

- Use `P-AC-1`–`P-AC-3`, the API/schema/scaffold portion of `P-AC-9`, and the conformance portion of `P-AC-8`. Preserve Core's local-ID FK rule and the shared target model. No blocking design decision remains.

**Readiness**

Ready for a task plan.

### Phase 2: Ingester validation and projection

**Goal**

Let the change-request ingester validate and package direct integer target IDs without translating them through a local entity.

**Focus**

- Accept the resolved value-source map in `IngesterConfig.extra`, including from standalone callers; keep an absent map on the existing path.
- Check values only on rows selected for the package after identity planning, with a required read-only target lookup in both table-based methods.
- Preserve direct IDs in packaged rows, apply FK missing-value rules, and identify direct-ID FKs in the manifest.

**Depends On**

- Phase 1's validated declaration and direct-FK conformance result.

**Outputs**

- An ingester that can validate and package direct-ID FKs from a standalone table caller, with no referenced project table for that FK.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-4`) A declared target ID reaches the packaged FK column unchanged and is never passed through the local `system_id` map.
- `PH2-AC-2` (from `P-AC-5`) Both `validate_tables()` and `ingest_tables()` reject malformed, absent, or unverifiable packaged IDs, naming the entity, column, and supplied value; standalone callers can provide the map.
- `PH2-AC-3` (from `P-AC-6`) Missing values fail on selected inserts when `required`, `required_when`, or `nullable: false` applies. An explicit null update to a non-nullable FK fails; an untouched FK update or excluded row does not require that value.
- `PH2-AC-4` (from `P-AC-7`) Integer target IDs are checked against the target table without a local-entity map; a non-integer target public-ID database column fails direct-mode validation.
- `PH2-AC-5` (from `P-AC-10`) The manifest identifies direct-ID FKs, and the mapping sidecar contains no artificial reconciliation link for supplied FK values.
- `PH2-AC-6` (from `P-AC-8`) Omitted and `system_id` value-source maps retain existing change-request projection results and diagnostics.

**Validation Milestones**

- `VM-2` (`PH2-AC-1`–`PH2-AC-6`): table-based validation and ingestion cover accepted IDs, lookup and type failures, row-action null rules, manifest content, and default-path parity.

**Task-Plan Handoff**

- Use `P-AC-4`–`P-AC-8` and `P-AC-10`. The target FK defines `required` and `required_when`; the database lookup is mandatory when packaged direct values exist. Preserve `required_when` insert timing and do not infer a source mode from table presence. No blocking design decision remains.

**Readiness**

Ready for a task plan.

### Phase 3: Saved-project delivery and end-to-end verification

**Goal**

Make saved-project validation and ingestion use the direct-ID path, then verify the documented feature against a target database.

**Focus**

- Derive the ingester's resolved map from a saved project and exercise both table-based methods through service callers.
- Complete user and agent guidance, regressions, a disposable PostgreSQL check, and a representative-project pilot.

**Depends On**

- Phase 1's resolved project declaration and Phase 2's validated ingester path.

**Outputs**

- A complete saved-project change-request flow, updated guidance, regression results, and a measured pilot result.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-1`) Saved-project callers derive and pass the resolved value-source map; an absent declaration retains the existing `system_id` path.
- `PH3-AC-2` (from `P-AC-5`) Saved-project validation and ingestion reach `validate_tables()` and `ingest_tables()`; a disposable PostgreSQL run accepts an existing ID and rejects a nonexistent or unverifiable ID before package acceptance.
- `PH3-AC-3` (from `P-AC-8`) Existing `system_id` projects retain their results and diagnostics, with known pre-existing standard-model failures separated from regressions.
- `PH3-AC-4` (from `P-AC-9`) The configuration guide explains the declaration and default; `AGENTS.md` and `src/AGENTS.md` distinguish Core local-ID links from direct target IDs in change-request packages. API and editor descriptions match the delivered behavior.
- `PH3-AC-5` (from `P-AC-3`) A representative project records how many otherwise optional helper entities it can remove while retaining any globally required entities.

**Validation Milestones**

- `VM-3` (`PH3-AC-1`–`PH3-AC-5`): saved-project and standalone paths agree, PostgreSQL checks exercise successful and failing IDs and manifest output, default projects match baseline results, guidance matches behavior, and the pilot count is recorded.

**Task-Plan Handoff**

- Use the saved-project portion of `P-AC-1` and `P-AC-5`, all of `P-AC-8` and `P-AC-9`, and the pilot from the proposal's testing section. Keep the default scaffold unchanged and use the existing table-based methods. No blocking design decision remains.

**Readiness**

Ready for a task plan.

## Cross-Phase Rules

- Keep Core project FK links on local `system_id` values; direct `public_id` values apply only to change-request package FK columns.
- Keep the shared target-model FK declaration authoritative and the default project path unchanged.
- Check direct IDs against the target database for packaged rows; fail when lookup is required but unavailable. Do not write supplied values as mapping-sidecar links.
- Preserve `required_when` insert timing and its exclusivity with `required`.

## Validation Strategy

Record the current standard-model conformance failures before changing behavior. Validate the declaration and conformance rules first (`VM-1`), then the ingester's table-based paths and row-action rules (`VM-2`). Finally, exercise saved-project calls and a disposable PostgreSQL package, compare existing `system_id` projects with the baseline, and record the pilot count (`VM-3`). Phase task plans select exact tests, fixtures, and commands.

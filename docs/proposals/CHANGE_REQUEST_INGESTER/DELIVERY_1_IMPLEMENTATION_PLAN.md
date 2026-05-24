# Delivery 1 Implementation Plan

## Purpose

This document turns the accepted Delivery 1 proposal decisions into an implementation plan and execution order.

It is not a new design proposal. It assumes the design decisions in [SEAD_CHANGE_REQUEST_INGESTER.md](./SEAD_CHANGE_REQUEST_INGESTER.md) are the current baseline.

## Delivery 1 Goal

Deliver a new ingester registered as `sead_change_request` that:

- accepts a DataFrame-first input contract
- resolves entity identities before SQL generation
- supports existing references, newly allocated entities, reconciled classifiers, SIMS-allocated classifiers, and derived bridge rows
- emits forward-only change-package artifacts only after Binding Set confirmation is complete
- stops with diagnostics and no partial artifacts when rows become `blocked_unresolved`

## Delivery 1 Non-Goals

- rollback implementation
- `UPDATE` or `DELETE` SQL generation
- resume-in-place after manual Binding Set confirmation
- semantic duplicate detection beyond target ID checks and metadata-defined bridge uniqueness checks
- broad refactoring of the existing ingester framework

## Implementation Principles

- Keep the ingester DataFrame-first internally even if a path-based adapter is required at the framework edge.
- Keep identity planning separate from SQL generation.
- Treat `blocked_unresolved` as a hard stop before any deploy, revert, or verify artifacts are emitted.
- Keep Delivery 1 synchronous at the change-package boundary.
- Use metadata-defined identity, unique, or composite-key rules where available. Do not guess when metadata is insufficient.

## Progress Checklist

Current implementation status as of 2026-05-24:

- [x] Workstream 1. Ingester scaffold
- [x] Workstream 2. Input contract and boundary types
- [x] Workstream 3. Target metadata and work planning
- [x] Workstream 4. Identity orchestration
- [x] Workstream 5. Binding Set confirmation handling
- [x] Workstream 6. PK and FK materialization
- [x] Workstream 7. Collision checks
- [x] Workstream 8. SQL and change-package generation
- [x] Workstream 9. SIMS association and audit linkage
- [x] Workstream 10. Validation, tests, and pilot

Notes:

- Delivery 1 is now closed on the current implementation baseline.
- Workstream 4 is complete. Row-state classification, reconciliation, real SIMS allocation for new entities and allocatable classifiers, and the real backend runtime path for derived bridge rows now work end to end.
- Workstream 2 is now complete for the current Delivery 1 boundary. The ingester accepts in-memory table bundles and path-based Excel workbook input, and it adapts workbook sheets into the internal source-bundle contract.
- Workstream 5 is now implemented for the current runtime contract. The ingester reads Binding Set state, attempts synchronous confirmation, and falls back to a pending confirmation report when confirmation still cannot complete.
- Workstream 8 now emits the generated artifact bundle to the configured output folder, including deploy SQL, metadata, and fail-loud revert and verify placeholders.
- Workstream 9 now associates the requested change request name with the confirmed Binding Set when both are available during the run.
- Workstream 10 is closed for Delivery 1. Focused tests cover the executable mixed pilot and the current artifact shape with deploy, revert, verify, and metadata outputs. Post-Delivery-1 improvements and further operational hardening now move to [DELIVERY_1_FOLLOWUP_CR.md](./DELIVERY_1_FOLLOWUP_CR.md).

## Detailed Workstream Checklist

### Workstream 1 Checklist

- [x] Create `ingesters/sead_change_request/`
- [x] Register key `sead_change_request`
- [x] Add metadata, validation entry point, and ingestion entry point
- [x] Make the ingester registry-visible and smoke-testable

### Workstream 2 Checklist

- [x] Implement the DataFrame-first ingester contract
- [x] Define `SubmissionContext`
- [x] Define change-package and deploy-artifact boundary types
- [x] Implement the path-based adapter from framework input to in-memory bundle

### Workstream 3 Checklist

- [x] Extract entity role, target table, public ID, and FK metadata needed by Delivery 1
- [x] Partition entity rows by populated versus missing `public_id`
- [x] Build deterministic per-row work plans
- [x] Surface early diagnostics when metadata is insufficient for bridge handling

### Workstream 4 Checklist

- [x] Implement Delivery 1 row-state classification
- [x] Resolve existing entities through `public_id`
- [x] Reconcile classifiers where existing matches are expected
- [x] Allocate new entities and allocatable classifiers through a real SIMS path that returns target-facing integer IDs
- [x] Implement the real backend runtime path for derived bridge rows
- [x] Mark unresolved rows as `blocked_unresolved`

### Workstream 5 Checklist

- [x] Read Binding Set state inside the Delivery 1 run
- [x] Stop before SQL generation when confirmation is still pending
- [x] Emit a pending confirmation report instead of partial artifacts
- [x] Confirm the Binding Set synchronously during the Delivery 1 run when the workflow allows it

### Workstream 6 Checklist

- [x] Replace local `system_id` values with resolved target-facing IDs
- [x] Materialize FK references for reference-only rows and inserted rows
- [x] Ensure bridge rows are based on resolved parent IDs where resolved IDs exist

### Workstream 7 Checklist

- [x] Add read-only target DB checks for planned inserts
- [x] Check target ID collisions
- [x] Check bridge-row uniqueness using metadata-defined unique or composite keys where available
- [x] Stop with diagnostics when bridge uniqueness metadata is missing at collision-check time

### Workstream 8 Checklist

- [x] Generate forward-only `INSERT` SQL in one transaction
- [x] Assume deferred FK checks in the generated deploy artifact
- [x] Generate an in-memory deploy artifact
- [x] Generate a fail-loud non-revertible revert placeholder
- [x] Generate a fail-loud compatibility verify placeholder
- [x] Mark package metadata as non-revertible
- [x] Emit the artifact bundle to its final operational file/package shape

### Workstream 9 Checklist

- [x] Associate generated CR name with the confirmed Binding Set
- [x] Persist submission metadata needed for auditability beyond the in-memory artifact payload

### Workstream 10 Checklist

- [x] Add focused unit coverage for row planning, identity resolution, materialization, SQL generation, and public result surfacing
- [x] Add confirmation-block coverage for pending Binding Set cases
- [x] Add collision-check coverage
- [x] Run a mixed pilot with existing references, new provider-owned entities, classifiers, and bridge rows
- [x] Close Delivery 1 on the current artifact shape and move follow-up hardening to a separate CR

## Workstreams

### 1. Ingester Scaffold

Scope:

- create `ingesters/sead_change_request/`
- register key `sead_change_request`
- add metadata, validation entry point, and ingestion entry point

Outputs:

- registry-visible ingester
- minimal package structure
- smoke-testable instantiation path

Dependencies:

- none

### 2. Input Contract And Boundary Types

Scope:

- implement the DataFrame-first ingester contract
- define `SubmissionContext`
- define `ChangePackage`
- define any adapter needed from path-based invocation into the in-memory bundle

Outputs:

- explicit ingestion boundary
- explicit return type for generated artifacts and metadata
- test fixtures that can call the ingester without Excel or CSV dispatch assumptions

Dependencies:

- Workstream 1

### 3. Target Metadata And Work Planning

Scope:

- extract entity role, target table, primary key, public ID, FK, and bridge uniqueness metadata
- partition entity rows by populated versus missing `public_id`
- build a deterministic per-row work plan
- identify rows that require reconciliation, allocation, reference-only handling, or bridge evaluation

Outputs:

- row planning model
- deterministic classification inputs for identity orchestration
- early diagnostics when metadata is insufficient for bridge uniqueness decisions

Dependencies:

- Workstream 2

### 4. Identity Orchestration

Scope:

- implement Delivery 1 row-state classification
- resolve existing entities through `public_id`
- reconcile classifiers where existing matches are expected
- allocate new entities and allocatable classifiers through SIMS
- mark unresolved rows as `blocked_unresolved`

Outputs:

- row states: `existing_entity`, `newly_allocated_entity`, `reconciled_classifier`, `derived_bridge_row`, `blocked_unresolved`
- resolved target-facing IDs for all rows eligible for SQL emission
- diagnostics for rows that can neither reconcile nor allocate

Dependencies:

- Workstream 3

### 5. Binding Set Confirmation Handling

Scope:

- confirm Binding Set status inside the Delivery 1 run
- stop before SQL generation when manual confirmation is still pending
- emit a pending confirmation report instead of partial artifacts

Outputs:

- synchronous confirmation behavior
- operator-facing pending confirmation report
- rerun instructions for blocked confirmation cases

Dependencies:

- Workstream 4

### 6. PK And FK Materialization

Scope:

- replace local `system_id` values with resolved target-facing IDs
- materialize FK references for reference-only rows and inserted rows
- ensure bridge rows are based on resolved parent IDs

Outputs:

- output-ready rows with only target-facing IDs in PK and FK positions
- no local `system_id` values in SQL inputs

Dependencies:

- Workstream 4
- Workstream 5

### 7. Collision Checks

Scope:

- add read-only target DB checks for planned inserts
- check target ID collisions
- check bridge-row uniqueness using metadata-defined unique or composite keys where available
- stop with diagnostics when bridge uniqueness metadata is missing

Outputs:

- collision diagnostics by table and key set
- explicit Delivery 1 idempotency boundary in output messages

Dependencies:

- Workstream 3
- Workstream 6

### 8. SQL And Change-Package Generation

Scope:

- generate forward-only `INSERT` SQL in one transaction
- assume deferred FK checks, with ordered insert fallback if validation proves necessary
- generate deploy artifact
- generate fail-loud non-revertible placeholders only if revert or verify files are required
- mark package metadata as non-revertible

Outputs:

- deploy artifact
- optional placeholder revert or verify artifacts
- package metadata linked to submission and Binding Set

Dependencies:

- Workstream 5
- Workstream 6
- Workstream 7

### 9. SIMS Association And Audit Linkage

Scope:

- associate generated CR name with the confirmed Binding Set
- persist submission metadata needed for auditability

Outputs:

- change package traceable to submission context and Binding Set

Dependencies:

- Workstream 8

### 10. Validation, Tests, And Pilot

Scope:

- add unit coverage for row planning, state classification, allocation and reconciliation paths, FK materialization, collision checks, and SQL generation
- add confirmation-block integration coverage
- run a mixed pilot with existing references, new provider-owned entities, classifiers, and bridge rows

Outputs:

- executable confidence for Delivery 1 acceptance criteria
- pilot evidence for artifact compatibility and operator workflow

Dependencies:

- Workstreams 1 through 9

## Execution Order

Recommended order:

1. Scaffold ingester package and registration.
2. Implement the DataFrame-first contract and boundary types.
3. Build target metadata extraction and row planning.
4. Implement identity orchestration, including classifier reconciliation and allocation.
5. Implement Binding Set confirmation handling.
6. Materialize PK and FK values from resolved identities.
7. Implement target-side collision checks.
8. Generate deploy and required placeholder artifacts.
9. Associate CR metadata in SIMS.
10. Run focused tests, then a mixed pilot.

## Suggested Issue Breakdown

### Issue 1. Scaffold Ingester Package

Includes:

- package layout
- registry registration
- metadata
- minimal constructor and entry points

Exit criteria:

- ingester appears in registry-backed listings
- constructor path is testable

### Issue 2. Implement Input Contract

Includes:

- `SeadChangeRequestIngester.ingest(...)`
- `SubmissionContext`
- `ChangePackage`
- optional adapter boundary

Exit criteria:

- DataFrame-first contract is documented and testable
- path-based compatibility, if needed, is only an adapter

### Issue 3. Implement Row Planning

Includes:

- metadata extraction
- entity new/existing rule using missing `public_id` only
- bridge uniqueness rule loading
- initial row work plan

Exit criteria:

- deterministic row planning exists
- missing bridge uniqueness metadata fails clearly

### Issue 4. Implement Identity Resolution

Includes:

- SIMS allocation for new entities
- reconciliation-first classifier handling
- SIMS allocation fallback for classifiers
- real backend runtime support for derived bridge rows
- `blocked_unresolved` classification

Exit criteria:

- all SQL-eligible rows have resolved state and IDs
- unresolved rows fail with actionable diagnostics

### Issue 5. Implement Confirmation Handling

Includes:

- synchronous Binding Set confirmation
- pending confirmation report
- no partial artifact behavior

Exit criteria:

- manual confirmation block produces report and no SQL package

### Issue 6. Implement PK/FK Materialization

Includes:

- PK replacement
- FK replacement
- bridge-row dependency materialization

Exit criteria:

- SQL inputs contain no local `system_id`

### Issue 7. Implement Collision Checks

Includes:

- target ID collision checks
- metadata-backed bridge uniqueness checks
- explicit limited-idempotency diagnostics

Exit criteria:

- collisions report table and key details
- metadata gaps block safely

### Issue 8. Implement SQL And Package Generation

Includes:

- deploy SQL
- transaction wrapper
- optional fail-loud placeholders
- non-revertible metadata

Exit criteria:

- artifact package is reviewable and workflow-compatible

### Issue 9. Implement SIMS Association

Includes:

- CR name association
- audit metadata persistence

Exit criteria:

- package is traceable to Binding Set and submission context

### Issue 10. Test And Pilot

Includes:

- unit and integration coverage
- mixed pilot scenario
- operator review of placeholder and confirmation behavior

Exit criteria:

- Delivery 1 acceptance criteria are satisfied
- pilot confirms artifact contract and exposes Delivery 2 gaps

## Exit Gate For Delivery 1

Delivery 1 is ready when all of the following are true:

- the ingester is registered as `sead_change_request`
- the DataFrame-first contract is documented and exercised in tests
- row-state handling covers existing references, new allocations, reconciled classifiers, allocatable classifiers, derived bridge rows, and blocked unresolved rows
- no SQL is emitted before identity resolution and Binding Set confirmation complete
- collision checks are in place for target IDs and metadata-defined bridge uniqueness keys
- package metadata is explicitly non-revertible when placeholders are used
- the mixed pilot succeeds or produces understood blocking diagnostics

Delivery 1 is now closed on that basis. Follow-up work on deploy-artifact strategy, templating, and target-model/schema review is tracked in [DELIVERY_1_FOLLOWUP_CR.md](./DELIVERY_1_FOLLOWUP_CR.md).

## Risks To Watch During Implementation

- metadata may not expose enough bridge uniqueness information for every target table
- classifier allocation policy may still need entity-type-specific exceptions after pilot data
- confirmation flow may be operationally acceptable in design but still awkward in real operator use
- deferred FK assumptions may fail on specific target tables and force ordered insert fallback sooner than planned

## Out Of Scope Follow-Up

These items belong after Delivery 1 unless pilot results force reprioritization:

- rollback implementation
- `UPDATE` generation
- richer semantic duplicate detection
- resumable long-running confirmation workflows
- generalized artifact naming policy across projects
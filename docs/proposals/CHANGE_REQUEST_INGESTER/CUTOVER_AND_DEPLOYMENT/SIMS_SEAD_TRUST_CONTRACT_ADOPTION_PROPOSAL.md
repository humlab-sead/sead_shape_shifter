# SIMS-SEAD Trust-Contract Adoption

## Status

- Proposed change
- Scope: operational adoption of SIMS-issued identities for SEAD tracked entities
- Goal: keep backfill, cutover, and deployment separate from the SIMS identity-allocation development work

Related documents: [completed SIMS identity-allocation phase plan](../done/SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md) and [SIMS-SEAD operational decisions](./SIMS_IDENTITY_ALLOCATION_OPERATIONAL_PLAN.md).

## Summary

Move the existing-data backfill, SIMS-SEAD trust adoption, cutover, and deployment into a separate operational workstream for CHANGE_REQUEST_INGESTER. The development CR remains focused on SIMS and Shape Shifter behavior. SEAD schema and writer changes continue through Sqitch change requests.

Backfill the existing SEAD identities into an initially empty SIMS store without changing their IDs or UUIDs. Require every tracked SEAD row to have a matching SIMS identity. Do not require every SIMS identity to have a SEAD row. Do not add cross-schema foreign keys; treat identity drift as a SEAD operational bug and detect it with validation checks.

## Problem

The development plan covers the SIMS identity contract and Shape Shifter integration, but adoption also requires historical data migration, SEAD writer changes, and coordinated deployment. Mixing these operational changes into the development CR would combine different owners and validation requirements.

## Scope

- Backfill existing tracked SEAD identities into an initially empty SIMS identity store.
- Resolve the tracked entity set and the SEAD-to-SIMS entity-type mapping.
- Add and populate UUID columns for tracked SEAD tables that lack them.
- Validate SEAD-to-SIMS identity coverage and correct any mismatches.
- Validate SEAD persistence and artifact behavior against the agreed target-system contract.
- Coordinate SEAD writer changes, SIMS allocator initialization, cutover, package supersession, and deployment through the appropriate Change Control work.

## Non-Goals

- Further SIMS or Shape Shifter development covered by the development CR.
- Cross-schema foreign keys or a SIMS responsibility for SEAD database integrity.
- Mapping SIMS identities to SEAD table or column names inside SIMS.
- Treating a SIMS-only identity as an orphan or validation failure.

## Current Behavior

SIMS has an identity store and allocation path, but existing SEAD tracked rows need to be registered in SIMS before the trust contract can cover historical data. The operational decision draft identifies six SEAD tables and reports missing UUID columns on `tbl_physical_samples` and `tbl_analysis_entities`. The exact mapping from those tables to configured SIMS entity types remains to be confirmed before backfill scripts are finalized.

## Proposed Design

### Separate operational work

Keep backfill, SEAD schema and writer changes, cutover, and deployment outside the development CR. Record SEAD database changes through Sqitch and group the related operational proposals and follow-up plans under this directory.

### Backfill existing identities

Start with an empty SIMS identity store. For each in-scope SEAD row, register the existing SEAD primary key as `aggregate_id` and preserve its UUID as `tracked_identity_uuid`. Do not reconcile, remap, or allocate replacement identities during backfill. Make reruns safe; skip exact matches and stop on conflicting IDs or UUIDs.

Before the backfill is treated as complete, resolve the SIMS entity-type mapping and ensure each tracked SEAD table has a UUID value. For tables missing UUID columns, add and populate those columns through SEAD change control, then use the same UUID values in SIMS.

### Validate identity coverage

Use read-only checks to confirm that every tracked SEAD row has exactly one matching SIMS identity for its entity type and aggregate ID, with matching UUIDs where the SEAD UUID column exists. Any missing or mismatched SIMS identity for a SEAD row blocks adoption and is handled as an operational bug. SIMS identities without SEAD rows are allowed.

Do not add cross-schema foreign keys. They are not the chosen response to identity drift; SEAD-owned checks will detect drift, and operational owners will investigate and correct it.

### Validate SEAD persistence and artifacts

SEAD-owned validation must confirm that the target system persists the generated artifact as intended. This checks SEAD's persistence and artifact contract; it does not assign database-integrity enforcement to SIMS.

### Coordinate cutover and deployment

Use SEAD Change Control for writer and schema changes. Include any Sqitch change request that can write tracked entities before backfill is complete; do not apply a new tracked-entity writer CR after backfill completion. Initialize SIMS allocators above the existing SEAD IDs before enabling new allocations. At cutover, new tracked identities come from SIMS and SEAD consumes those identities rather than minting them through its sequences.

Confirm that the submission schema, required legacy migration, and any required compatibility behavior are deployed before generated packages become eligible. The upstream release and compatibility-view owner remain to be confirmed.

The [PostgreSQL contract validation handoff](./POSTGRESQL_CONTRACT_VALIDATION.md) records a current blocker: disposable tests found that both generated artifact strategies explicitly insert submission and dataset IDs without advancing their database sequences. The next default-generated IDs can therefore collide. Do not deploy those test packages. Resolve the identity and sequence contract, then verify sequence safety for both strategies against disposable database clones.

Define deployment and package-supersession gates in the operational delivery plan. A regenerated package must not become eligible until its earlier package for the same logical submission has been withdrawn or superseded. SIMS Binding Set state remains audit state and does not revoke generated SQL.

### Deferred development follow-up

Manual SIMS Binding Set confirmation, automatic expiry or supersession of pending sets, and insertion paths for unsupported child or derived rows remain separate development follow-up. This operational proposal records them as dependencies to track; it does not implement or validate them.

## Alternatives Considered

- **Cross-schema foreign keys:** Rejected. The selected approach detects and corrects identity drift through SEAD-owned validation rather than coupling SEAD writes to SIMS rows.
- **Require no SIMS-only identities:** Rejected. SIMS may contain allocated identities that have not yet been materialized in SEAD.

## Risks And Tradeoffs

- Verification checks detect drift but do not prevent it at write time. Adoption therefore depends on running the checks and treating any unmatched SEAD row as a blocking bug.
- The backfill cannot be finalized until the tracked entity set and entity-type mapping are unambiguous.
- Deployment ordering must respect the rule that no tracked-entity writer CR is applied after backfill completion.
- Explicit IDs in generated artifacts can leave SEAD sequences behind and cause later default-generated IDs to collide; both current test strategies fail the recorded sequence check.

## Testing And Validation

- Compare all tracked SEAD rows with SIMS by entity type and aggregate ID; require no missing or mismatched SIMS identity.
- Compare UUID values for every tracked SEAD table after the missing UUID columns are added and populated.
- Confirm SIMS allocator values are above existing SEAD IDs before new allocation is enabled.
- Verify the writer-CR and deployment gates, including package withdrawal or supersession before a regenerated package becomes eligible.
- Confirm SIMS-only rows do not fail the SEAD coverage check.
- Confirm SEAD persistence and artifact checks meet the target-system contract without relying on SIMS to enforce SEAD integrity.
- Apply each artifact strategy to its own disposable clone and verify that subsequent default-generated IDs cannot collide with explicitly inserted IDs.

## Acceptance Criteria

- `P-AC-1`: Every tracked SEAD row in scope is represented in SIMS with its existing aggregate ID and UUID; backfill reruns do not create duplicates or silently accept conflicting identities.
- `P-AC-2`: Every tracked SEAD table has a UUID value, and the SEAD and SIMS values match.
- `P-AC-3`: Coverage checks find no tracked SEAD row without a matching SIMS identity; SIMS-only identities are allowed.
- `P-AC-4`: No tracked-entity writer Sqitch CR is applied after backfill completion, and new tracked identities are issued by SIMS after cutover.
- `P-AC-5`: Deployment validation includes package withdrawal or supersession before a regenerated package becomes eligible.
- `P-AC-6`: The operational work remains separate from the development CR, and no cross-schema foreign key is introduced for this trust contract.
- `P-AC-7`: SEAD-owned validation confirms the target system's persistence and artifact contract; it does not rely on SIMS to enforce SEAD database integrity.
- `P-AC-8`: Both generated artifact strategies pass post-package sequence-safety checks on disposable databases before deployment; packages that leave sequences behind explicit IDs are not eligible.

## Planning Handoff

After this proposal is approved, create a separate operational delivery plan under `CHANGE_REQUEST_INGESTER/CUTOVER_AND_DEPLOYMENT`. It should define the Change Control CR ordering, backfill and verification procedures, deployment gates, and owners without adding those tasks to the development CR.

Preserve these decisions: SIMS starts empty for backfill; existing SEAD IDs and UUIDs are retained; every tracked SEAD row must match SIMS; SIMS-only rows are allowed; identity drift is a SEAD operational bug; no tracked-entity writer CR is applied after backfill completion; and SEAD remains responsible for its database integrity.

Resolve the SIMS entity-type mapping, UUID migration order, upstream schema release and compatibility ownership, artifact sequence safety, and package-supersession gates before finalizing executable work.

## Open Questions

- Does SEAD `tbl_physical_samples` map to SIMS entity type `sample` or `physical_sample`? The current SIMS policy uses `sample`, while the operational backfill draft names `physical_sample`.
- Should the missing UUID columns be added and populated before backfill? The same UUID must ultimately be present in SEAD and SIMS.
- Which Change Control CRs and deployment gates implement the writer transition and package-supersession requirement?
- Which upstream release provides the submission schema, and which component owns legacy compatibility views and their removal schedule?

## Final Recommendation

Approve a separate operational workstream for CHANGE_REQUEST_INGESTER cutover and deployment. Keep the development CR focused on the implemented SIMS and Shape Shifter contract; complete and validate the SEAD backfill and writer transition through SEAD Change Control before declaring operational adoption.

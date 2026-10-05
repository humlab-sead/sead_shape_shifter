# Cutover And Deployment

This folder collects the operational decisions and validation gates for adopting SIMS-issued identities in SEAD. It does not yet contain an approved, executable delivery plan; SEAD schema and writer changes must be scheduled through Change Control.

## Active Documents

- [SIMS-SEAD trust-contract adoption proposal](./SIMS_SEAD_TRUST_CONTRACT_ADOPTION_PROPOSAL.md) — adoption scope, cutover rules, deployment gates, and acceptance criteria.
- [SIMS identity allocation operational plan](./SIMS_IDENTITY_ALLOCATION_OPERATIONAL_PLAN.md) — backfill, cross-schema coverage, sequence ownership, and missing UUID decisions.
- [PostgreSQL contract validation handoff](./POSTGRESQL_CONTRACT_VALIDATION.md) — disposable-database procedure and the current generated-artifact blocker.
- [Submission metadata proposal](../REFACTOR_SEAD_SUBMISSION_METADATA.md) — implemented package contract and unresolved upstream schema dependencies.

## Gates To Resolve

1. Confirm the complete tracked-entity set and SIMS entity-type mapping, including whether `tbl_physical_samples` maps to `sample` or `physical_sample`.
2. Add and populate UUID columns for tracked SEAD tables that lack them, then preserve the same UUID values in SIMS.
3. Backfill existing SEAD IDs and UUIDs into an initially empty SIMS store. Require every tracked SEAD row to match SIMS; SIMS-only identities are allowed.
4. Order writer changes so no tracked-entity writer change is applied after backfill completes. Initialize SIMS allocators above existing SEAD IDs before new allocations are enabled.
5. Confirm the submission schema, required legacy migration, and any required compatibility behavior are deployed before generated packages are eligible. The upstream release and compatibility-view owner remain to be confirmed.
6. Resolve the generated-artifact sequence-safety failure before deployment. The current disposable test packages leave submission and dataset sequences behind explicitly inserted IDs; do not deploy those packages. Validate both inline INSERT and copy-CSV output after the identity and sequence contract is corrected.
7. Prevent a regenerated package from becoming eligible until the earlier package for the same logical submission has been withdrawn or superseded. SIMS Binding Set status does not revoke generated SQL.
8. Run SEAD-to-SIMS coverage, UUID parity, allocator, sequence-safety, and SEAD persistence checks before adoption. Do not use SIMS as the enforcement mechanism for SEAD database integrity.

Closed artifact-format and renderer work remains documented under [done/CHANGE_REQUEST_INGESTER_DELIVERY_1](../done/CHANGE_REQUEST_INGESTER_DELIVERY_1); it describes implementation history, not cutover approval.
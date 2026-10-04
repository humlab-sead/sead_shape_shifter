# Operational Plan (Draft): SIMS–SEAD Trust-Contract Adoption

## Status

Draft. Records the operational decisions for existing-data migration, cross-schema checks, sequence deprecation, and UUID schema gaps. Rollout and cutover remain separate Change Control work. An operational delivery plan cannot be finalized until this plan and the separate deployment decisions referenced in the [phase plan](../SIMS_IDENTITY_ALLOCATION/SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md) are approved.

## Summary

SIMS currently mints identities for new data only. The trust contract requires every tracked entity already represented in SEAD to also have a SIMS identity, and SIMS to become the sole minter going forward. This plan fixes the adoption method:

- **Backfill** SEAD's existing tracked identities into SIMS unchanged — no reconciliation, no remapping, reusing existing internal IDs and UUIDs.
- **Check SEAD-to-SIMS coverage** without hard foreign keys; an unmatched SEAD row is a bug, while a SIMS identity without a SEAD row is allowed.
- **Deprecate SEAD sequence minting** for tracked entities so new SEAD rows use SIMS-issued identities instead of `nextval`.
- **Defer rollout and cutover** to separate SEAD Change Control CRs.
- **Add the missing UUID columns** in SEAD for tracked entities that lack them.

## Problem

The trust contract is satisfied automatically for new allocations: SIMS mints, SEAD consumes. It is not satisfied for data that predates SIMS. Those rows have SEAD-minted integer keys (and, for most entities, a UUID) but no corresponding `sead_identity.tracked_identities` row. Until that correspondence exists for every tracked entity, SIMS cannot be treated as the sole minter, and the contract cannot be declared in force.

Two further gaps block adoption: some tracked entity tables have no UUID column at all, and SEAD still mints new identities through its own sequences, which would keep producing identities SIMS has no record of.

## Scope And Owners

- **Owner:** SEAD and SIMS operational owners. Shape Shifter and Change Control participate in their respective integration responsibilities.
- **In scope:** the backfill method and scripts; the cross-schema integrity assessment; the sequence-deprecation CR review; the missing-UUID schema additions.
- **Out of scope:** rollout/cutover sequencing (separate CRs); any SIMS mapping of identities to SEAD tables or columns; assigning SEAD database-integrity guarantees to SIMS.
- **System rules preserved:** SIMS guarantees uniqueness only within its own identity store. SEAD owns its persistence constraints. SIMS Binding Set state is audit state and does not revoke generated SQL.

## Decisions

### D1 — Migration method: backfill SEAD → SIMS, no reconciliation, no remapping

SIMS starts empty for this backfill. Existing tracked identities in SEAD are backfilled into SIMS as-is. Each backfilled `tracked_identity` reuses the SEAD row's existing internal ID and UUID where present; nothing is reconciled against an external source and no identity is remapped to a fresh value. SEAD writes are controlled through Sqitch change requests; no new writer CR is applied after the backfill until the SIMS-consuming path is in place, so the backfilled SEAD rows remain the adoption baseline.

**Direction confirmed:** existing SEAD identities are registered *into SIMS* (`sead_identity.tracked_identities`) so every tracked SEAD entity gains a SIMS row.

Backfill scripts must, per entity type:

- read each tracked SEAD table (`tbl_sites`, `tbl_sample_groups`, `tbl_physical_samples`, `tbl_datasets`, `tbl_analysis_entities`, `tbl_submissions`);
- insert one `sead_identity.tracked_identities` row using `aggregate_id = <*_id>` and `tracked_identity_uuid = <*_uuid>` (with a generated UUID where no `*_uuid` exists, pending D5);
- be idempotent (re-runnable), record inserted vs already-present rows, and fail if an existing SIMS row disagrees with its SEAD identity.

### D2 — Cross-schema integrity: verification checks, not hard foreign keys

SIMS tables live in the `sead_identity` schema; SEAD tables live in the `public` schema. Both are in the same database, and PostgreSQL supports cross-schema foreign keys. SEAD will not use them for this contract: identity drift is an operational bug to detect and correct under SEAD's broader quality and assurance work, not a reason to couple the two schemas with a new FK.

The read-only coverage check must find no tracked SEAD row without a matching SIMS `(entity_type, aggregate_id)`, and must compare UUIDs where SEAD has a UUID column. A SIMS identity without a SEAD row is allowed and must not fail coverage. Run the check after backfill and as part of SEAD-owned validation; any missing or mismatched SEAD identity blocks adoption and must be investigated as a bug.

### D3 — Deprecate SEAD sequence minting for tracked entities

SEAD mints PKs through `public` sequences for every tracked entity (`tbl_sites_site_id_seq`, `tbl_sample_groups_sample_group_id_seq`, `tbl_physical_samples_physical_sample_id_seq`, `tbl_datasets_dataset_id_seq`, `tbl_analysis_entities_analysis_entity_id_seq`, `tbl_submissions_submission_id_seq`).

All SEAD changes are recorded in SEAD Change Control. Review the CRs that mint new identities for tracked entities so future writes use SIMS-issued identities instead of calling `nextval`. Existing SEAD identities registered by the backfill keep their original values; new allocations must come from SIMS. Initialize each SIMS allocator above the existing SEAD IDs before enabling new allocations. Removing a sequence default from an existing table is a separate DDL CR; the immediate goal is to stop new SEAD mints, not necessarily to drop the sequences.

This review is a SEAD Change Control task, delivered as one or more CRs.

### D4 — Rollout and cutover are separate CRs

Rollout and cutover are excluded from this operational plan. They belong to the SEAD change-request ingester rollout and will be handled in separate Change Control CRs. Those decisions must be approved before the operational delivery plan can be finalized.

### D5 — Add missing UUID fields in SEAD for tracked entities

Verified against the SEAD schema snapshot and `sead_model` DDL:

| Tracked entity | SEAD table | `*_uuid` column | Status |
| --- | --- | --- | --- |
| `site` | `tbl_sites` | `site_uuid` | present |
| `sample_group` | `tbl_sample_groups` | `sample_group_uuid` | present |
| `dataset` | `tbl_datasets` | `dataset_uuid` | present |
| `submission` | `tbl_submissions` | `submission_uuid` | present (20260830 submission model) |
| `physical_sample` | `tbl_physical_samples` | — | **missing** |
| `analysis_entity` | `tbl_analysis_entities` | — | **missing** |

`tbl_physical_samples` and `tbl_analysis_entities` need new `physical_sample_uuid` and `analysis_entity_uuid` columns. This is a SEAD Change Control schema change (DDL CRs). The backfill can proceed for these two entities using `aggregate_id` correspondence before the UUID columns exist, but the UUID is required for the full contract, so the columns must be added.

## Repository Findings

**Repository basis:** planning date 2026-10-04. Findings below are from the current workspace snapshots; the `table-schema-detailed.csv` may lag the newest `sead_model` CRs and should be regenerated from the live database before the backfill scripts are finalized.

| Evidence | Finding | Planning implication |
| --- | --- | --- |
| `sead_authority_service/schema/sql/identity/000_schema.sql` | SIMS tables live in the `sead_identity` schema. | Cross-schema checks target `sead_identity.*`. |
| `sead_authority_service/schema/sql/identity/005_tracked_identities.sql`, `010_aggregate_identity_value.sql` | `tracked_identities` has `tracked_identity_uuid` (PK) and `aggregate_id bigint` (formerly `sead_internal_id`), scoped by `entity_type`. | Backfill writes `aggregate_id` + `tracked_identity_uuid` per `entity_type`. |
| `sead_change_control/.../SEAD_DATABASE_MODEL/archive/sequences.sql` | SEAD sequences are `"public"."tbl_*_seq"`. | SEAD data is in `public`; sequence minting is confirmed for tracked entities. |
| `sead_change_control/sead_model/deploy/SEAD_DATABASE_MODEL/tables.sql` | Tracked entity PKs are `serial`/`bigserial`. | Confirms D3 sequence minting. |
| `sead_change_control/sead_model/deploy/20260830_DDL_SUBMISSION_MODEL_REFACTOR.sql` | `tbl_submissions` has `submission_uuid uuid not null default uuid_generate_v4() unique`. | `submission` UUID is present. |
| `sead_change_control/.../table-schema-detailed.csv` | `tbl_physical_samples` and `tbl_analysis_entities` have no `*_uuid` column. | Confirms D5 gap. |

## Open Questions

1. **Tracked-entity closure.** The exact set of SIMS-tracked entity types should be pinned to `sead_authority_service/config/identity_policy.yml` before scripts are written; the table list above is the schema-level view and must be reconciled with the policy.
2. **Missing UUIDs.** For entities without a SEAD UUID column (D5), decide whether to add and populate the column before backfill or to generate the UUID during backfill and write that same value to SEAD before adoption.

## Next Steps

1. Pin the tracked-entity set to `identity_policy.yml`.
2. Review the SEAD writer CRs and prepare the missing-UUID schema CRs before fixing the backfill baseline.
3. Write and review the idempotent backfill scripts (per entity type) and the SEAD-to-SIMS coverage checks (D2).
4. Define the separate rollout and cutover CRs (D4), including when SEAD stops minting and SIMS allocation begins.
5. Once this plan and the separate rollout and cutover decisions are approved, create an operational delivery plan based on the [standalone cutover and deployment proposal](./CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md).

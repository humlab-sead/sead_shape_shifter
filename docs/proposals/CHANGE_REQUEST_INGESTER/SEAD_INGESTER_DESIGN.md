# Proposal: SEAD Change Request Ingester

## Status

- Proposed replacement for the current Clearinghouse ingester (`ingesters/sead/`)
- Scope: New ingester that generates Sqitch-ready SQL DML from normalized DataFrames
- Goal: Eliminate the Clearinghouse staging layer and generate change requests directly

## Summary

Replace the current SEAD Clearinghouse ingester with a new ingester that transforms normalized DataFrames directly into Sqitch-ready SQL change requests. The new ingester uses the fully implemented SIMS API (via `SimsClient`) to resolve all entity identities before SQL generation — reconciling existing entities and allocating IDs for new ones. This eliminates the Clearinghouse CSV staging layer, the Transport System, and the manual ID reconciliation steps.

The building blocks exist: SIMS is live in `sead_authority_service`, `SimsClient` is implemented in Shape Shifter, target model conformance validators are active, and the ingester framework supports pluggable discovery. What remains is the ingester implementation itself.

## Problem

The current SEAD ingester (`ingesters/sead/`) produces a Clearinghouse submission:

```
Normalized DataFrames → CSV (4 files) → Clearinghouse staging tables → stored procedures → public schema
```

This workflow has several problems:

1. **Indirect path.** DataFrames are serialized to CSV, loaded into staging tables, then moved to public tables via stored procedures. Each step is a failure point.
2. **No identity resolution.** The Clearinghouse uses `system_id`/`public_id` conventions to distinguish new vs. existing records, but has no formal identity resolution. Reconciliation is manual and error-prone.
3. **No change control integration.** The output is a database state change, not a versioned change request. There is no Sqitch script, no rollback plan, no audit trail.
4. **Tight coupling to Clearinghouse schema.** The ingester depends on `clearing_house.tbl_clearinghouse_submission_*` tables and PostgreSQL stored procedures that are specific to the Clearinghouse design.
5. **No idempotency guarantee.** Re-running the same data can create duplicate records because identity is not tracked across submissions.

SIMS solves the identity problem. This ingester uses SIMS to close the remaining gaps.

## Scope

This proposal covers:

- A new ingester registered as `sead_cr` (or similar) under the existing ingester framework
- Identity resolution for all entities via SIMS (`SimsClient`)
- Foreign key resolution from local `system_id` to SIMS-allocated SEAD integer IDs
- SQL DML generation (INSERT statements) with topological ordering
- Sqitch change request output (deploy/revert scripts)
- Binding Set confirmation and change request association via SIMS

## Non-Goals

- Modifying Shape Shifter core pipeline (extract, filter, link, unnest, translate)
- Modifying SIMS internals — this ingester is a SIMS API consumer
- DDL generation — only DML (INSERT/UPDATE)
- Replacing the CSV/Excel dispatchers — they remain available for non-SEAD use cases
- Real-time database writes — the output is SQL files, not direct execution

## Current Behavior

### Current ingester pipeline (`ingesters/sead/`)

```
Excel → Submission (DataFrames)
  → Policies (add PKs, resolve FKs, map system_id → public_id)
  → Specifications (validate schema, types, FKs)
  → CsvProcessor (generate 4 CSV files: tables, columns, records, recordvalues)
  → SubmissionRepository (upload CSV to Clearinghouse staging tables)
  → Explode (stored procedures copy staging → public schema)
```

Key characteristics:
- Policies and specifications are registry-based (auto-registered via decorators)
- FK resolution uses `system_id` → `public_id` mapping from `mappings.yml`
- New records have NULL `public_id`; existing records have non-NULL `public_id`
- No formal identity lifecycle — no UUID tracking, no binding confirmation

### What exists and is reusable

| Component | Location | Reuse in new ingester |
|-----------|----------|-----------------------|
| SIMS (identity resolution, allocation, binding) | `sead_authority_service/src/identity/` | Consumed via `SimsClient` |
| `SimsClient` (async HTTP client) | `backend/app/clients/sims_client.py` | Direct use — wraps all 6 SIMS endpoints |
| SIMS DTOs | `backend/app/models/sims.py` | Direct use — request/response models |
| Target model metadata | `sead_standard_model.yml` | Entity roles, identity columns, FK specs, target tables |
| Ingester framework | `backend/app/ingesters/` | Protocol, registry, discovery |
| Topological sort | `backend/app/utils/graph.py` | Entity dependency ordering |
| `mappings.yml` reconciliation | Shape Shifter core | Pre-resolved identities for known entities |

## Proposed Design

### Architecture

```
Normalized DataFrames (from Shape Shifter core)
        │
        ▼
┌─────────────────────────────────────────────┐
│ SEAD Change Request Ingester                │
│                                             │
│  1. Load target model metadata              │
│  2. Build identity signals from DataFrames  │
│  3. Resolve all identities via SIMS         │
│  4. Confirm Binding Set                     │
│  5. Build system_id → SEAD ID mapping       │
│  6. Resolve foreign keys                    │
│  7. Generate SQL (topological order)        │
│  8. Emit Sqitch change request              │
│  9. Associate CR name with Binding Set      │
│                                             │
│  SimsClient ◄──── HTTP ────► SIMS API      │
└─────────────────────────────────────────────┘
        │
        ▼
Sqitch deploy/revert SQL scripts
```

### Key principle: all identities resolved before SQL generation

A change request must not be emitted until every entity referenced in it has a resolved SEAD identity. This means:

- Every row in every entity table has either been reconciled to an existing SEAD entity (matched) or allocated a new SEAD ID (new).
- The resolution is captured in a confirmed SIMS Binding Set.
- Foreign key columns reference resolved SEAD integer IDs, not local `system_id` values.

If any identity resolution fails (e.g., a shared metadata entity cannot be matched and allocation is blocked by policy), the ingester aborts before generating SQL. No partial output.

### Step-by-step flow

#### 1. Load target model metadata

Read `sead_standard_model.yml` to get per-entity metadata: `target_table`, `public_id`, `identity_columns`, `foreign_keys`, `role`.

This drives which columns to include in SQL, how to name FK columns, and the topological ordering.

#### 2. Build identity signals from DataFrames

For each entity row, construct a SIMS `ResolutionRequest`:

- **`entity_type`**: entity name from target model (e.g., `site`, `sample_group`)
- **`primary_signal`**: business key derived from `identity_columns` in the target model
- **`additional_signals`**: any supplementary identity signals (e.g., from `mappings.yml` pre-resolution)

Entities already fully mapped in `mappings.yml` (i.e., all rows have a known SEAD ID) can skip SIMS resolution — they are pre-resolved.

#### 3. Resolve all identities via SIMS

Call `SimsClient.resolve()` with a batch of `ResolutionRequest` items:

```python
response: ResolveResponse = await sims_client.resolve(ResolveRequest(
    scope_name=f"sead://shapeshifter/{project_name}",
    submission_name=submission_name,
    requests=resolution_requests,
    created_by="shapeshifter",
))
```

SIMS returns a `ResolveResponse` containing:
- A `BindingSetResponse` (proposed or auto-confirmed)
- A list of `ResolutionOutcome` per entity (matched or new, with `tracked_identity_uuid`)

For provider-owned entities (site, sample_group, sample, etc.), SIMS auto-confirms the Binding Set and allocates SEAD IDs. For shared metadata entities (method, taxa, etc.), the Binding Set may remain proposed and require manual confirmation.

#### 4. Confirm Binding Set

If the Binding Set is not auto-confirmed:

```python
binding_set = await sims_client.confirm_binding_set(binding_set_uuid)
```

The ingester must wait for confirmation before proceeding. This is the gate that enforces the "all identities resolved" principle.

#### 5. Build system_id → SEAD ID mapping

From the resolution outcomes, build a mapping table:

```
entity_type | system_id | tracked_identity_uuid | sead_id (integer)
site        | 1         | a1b2c3d4-...          | 4821
site        | 2         | e5f6g7h8-...          | 4822
sample      | 1         | i9j0k1l2-...          | 91204
```

The `sead_id` comes from `TrackedIdentity.sead_internal_id` — the integer PK allocated by SIMS.

#### 6. Resolve foreign keys

Replace local `system_id` FK references with resolved SEAD integer IDs:

```
Before: sample_group.site_id = 1 (system_id)
After:  sample_group.site_id = 4821 (SEAD site_id)
```

Use the target model's `foreign_keys` spec to identify FK columns and their parent entities. The topological sort ensures parents are resolved before children.

#### 7. Generate SQL

For each entity in topological order, generate INSERT statements:

```sql
INSERT INTO tbl_sites (site_id, site_name, ...)
VALUES (4821, 'Ageröd', ...);

INSERT INTO tbl_sample_groups (sample_group_id, site_id, sample_group_name, ...)
VALUES (8301, 4821, 'Context 1', ...);
```

- Column names from target model (`target_table`, column specs)
- Values from resolved DataFrames
- Parameterized generation to prevent SQL injection
- NULL handling per column spec

#### 8. Emit Sqitch change request

Wrap the SQL in Sqitch deploy and revert scripts:

**Deploy** (`deploy/CR_dendro_2026_01.sql`):
```sql
BEGIN;
-- Generated by Shape Shifter SEAD Change Request Ingester
-- Submission: dendro_2026_01
-- Binding Set: a1b2c3d4-...
-- Date: 2026-04-06

INSERT INTO tbl_sites ...;
INSERT INTO tbl_sample_groups ...;
INSERT INTO tbl_physical_samples ...;
-- ... (topological order)

COMMIT;
```

**Revert** (`revert/CR_dendro_2026_01.sql`):
```sql
BEGIN;
-- Revert: delete in reverse topological order
DELETE FROM tbl_physical_samples WHERE physical_sample_id IN (...);
DELETE FROM tbl_sample_groups WHERE sample_group_id IN (...);
DELETE FROM tbl_sites WHERE site_id IN (...);
COMMIT;
```

#### 9. Associate change request name with Binding Set

After generating the Sqitch scripts, register the CR name with SIMS:

```python
await sims_client.associate_change_request(binding_set_uuid, cr_name)
```

This links the identity resolution to the specific database change, enabling audit and traceability.

### Entity identity resolution by role

The target model assigns roles to entities. Resolution behavior varies by role:

| Role | SIMS behavior | Example entities |
|------|---------------|------------------|
| **fact** | Provider-owned. Allocate new ID, auto-confirm. | sample, abundance, geochronology |
| **lookup** | Provider-owned. Allocate new ID, auto-confirm. | site, sample_group, dataset |
| **classifier** | Shared metadata. Must match existing SEAD entity. Allocation blocked. | sample_type, method, taxa_tree_master |
| **bridge** | Relationship. Derived from parent identities. | analysis_entity, site_location |

The ingester must handle all four cases. Classifiers that cannot be matched cause the submission to fail with diagnostics.

### Integration with Shape Shifter's three-tier identity system

Shape Shifter uses three identity tiers (see AGENTS.md):

1. **`system_id`** — Local sequential (1, 2, 3...). Used for all FK relationships during normalization.
2. **`keys`** — Business keys for deduplication. Used as SIMS identity signals.
3. **`public_id`** — Target schema column name. Receives the allocated SEAD integer ID.

The ingester bridges tiers:

```
system_id (internal) ──► SIMS resolution ──► tracked_identity_uuid ──► sead_internal_id
                              ▲
                         keys (business key signals)
```

After resolution, `public_id` columns in the output SQL contain SEAD integer IDs, and FK columns reference parent SEAD IDs.

### Registration

The new ingester registers under the existing framework:

```python
@Ingesters.register(key="sead_cr")
class SeadChangeRequestIngester:
    """Generates Sqitch-ready SQL change requests from normalized DataFrames."""

    @classmethod
    def get_metadata(cls) -> IngesterMetadata:
        return IngesterMetadata(
            key="sead_cr",
            name="SEAD Change Request",
            description="Generates Sqitch-ready SQL DML via SIMS identity resolution",
            version="1.0.0",
            supported_formats=["dataframe"],
            requires_config=True,
        )
```

### Relationship to current ingester

The new ingester replaces `ingesters/sead/` over time:

1. New ingester is developed alongside the existing one under a different key (`sead_cr` vs `sead`)
2. Both are available during transition
3. Once validated, the old Clearinghouse ingester is deprecated and eventually removed

## Risks and Tradeoffs

| Risk | Mitigation |
|------|------------|
| SIMS unavailability blocks ingestion | Dry-run mode validates everything except SIMS calls; clear error on API failure |
| Shared metadata entities fail to match | Diagnostics returned from SIMS; ingester reports which entities need manual reconciliation |
| Large submissions may be slow (many SIMS round-trips) | Batch resolution API (single call per submission); future: parallel entity-type resolution |
| Sqitch script correctness | Dry-run + validation mode; revert scripts generated alongside deploy |
| Migration from Clearinghouse workflow | Parallel availability; no forced switch |

## Testing and Validation

### Unit tests

- Identity signal construction from DataFrames and target model metadata
- FK resolution from `system_id` to SEAD ID
- SQL generation: correct syntax, topological ordering, NULL handling
- Revert script generation (reverse topological order, correct ID sets)
- Error handling: unresolved identities block SQL generation

### Integration tests

- End-to-end: normalized DataFrames → SIMS resolution → SQL output
- SimsClient round-trip with test SIMS instance
- Idempotency: same input produces same output (same SEAD IDs)
- Binding Set lifecycle: propose → confirm → associate CR

### Validation mode

- Dry-run that checks target model conformance, identity signal completeness, and FK integrity without calling SIMS

## Acceptance Criteria

- [ ] All entity identities resolved (reconciled or allocated) before SQL generation
- [ ] No `system_id` values in output SQL — only SEAD integer IDs
- [ ] SQL topologically ordered (parents before children)
- [ ] Revert script generated for every deploy script
- [ ] Binding Set confirmed and CR name associated in SIMS
- [ ] Existing `mappings.yml` reconciliation honored (pre-resolved entities skip SIMS)
- [ ] Shared metadata entities that fail to match produce clear diagnostics
- [ ] Registered under ingester framework; discoverable via CLI and API
- [ ] Current Clearinghouse ingester unaffected during transition

## Recommended Delivery Order

1. **Scaffold**: Register new ingester, implement `get_metadata()` and `validate()` stubs
2. **Identity signal builder**: Construct `ResolutionRequest` from DataFrames + target model
3. **SIMS integration**: Wire `SimsClient.resolve()`, handle outcomes, build ID mapping
4. **FK resolution**: Replace `system_id` with SEAD IDs using the mapping
5. **SQL generation**: Topologically-ordered INSERT statements
6. **Sqitch output**: Deploy/revert script packaging
7. **Binding Set lifecycle**: Confirmation flow and CR name association
8. **Dry-run mode**: Validate without SIMS calls
9. **Pilot**: Test with real project data

## Open Questions

1. **Ingester key naming**: `sead_cr`, `sead_sql`, or reuse `sead` with a mode flag?
2. **Batch size limits**: Should large submissions be split into multiple SIMS resolution calls?
3. **Change detection**: Should the ingester use `SimsClient.detect_change()` for re-submissions, or is idempotent resolution sufficient?
4. **UPDATE vs INSERT**: Should the ingester support UPDATE statements for changed entities, or only INSERT for new data?
5. **Ingester protocol evolution**: The current `Ingester` protocol takes a file path (`source: str`). The new ingester consumes DataFrames. Should the protocol be extended, or should the ingester receive DataFrames through `IngesterConfig.extra`?

## Final Recommendation

Build the new ingester as `ingesters/sead_cr/` alongside the existing Clearinghouse ingester. Use `SimsClient` for all identity resolution. Enforce the invariant that no SQL is generated until every identity is resolved. Start with INSERT-only SQL and Sqitch script packaging. Iterate on change detection and UPDATE support after the core flow is validated with pilot data.
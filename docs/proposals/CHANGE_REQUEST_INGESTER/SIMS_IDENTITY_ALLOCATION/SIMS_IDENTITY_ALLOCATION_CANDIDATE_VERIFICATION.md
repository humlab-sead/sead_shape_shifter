# SIMS Identity Allocation — Candidate Verification Record

## Status

**Complete (2026-10-02).** Historical disposable verification of the initial `site` and `sample` examples. This is not a SIMS runtime allowlist, not capability configuration, and not cutover approval. The examples do not define entity-specific allocator code or limit the generic, configurable identity mechanism.

## Purpose

Records the disposable checks behind the initial examples in the [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md), under the [identity allocation contract](./SIMS_IDENTITY_ALLOCATION_CONTRACT.md). Shape Shifter approves reconciliation matches and misses; SIMS owns its configured tracked identities and minted aggregate identity values; SEAD consumes SIMS-issued values under the trust contract. `site_location` is an untracked bridge, not a SIMS tracked entity.

## Scope

Checks ran against the helper-owned disposable database only, via `scripts/verify_sims_identity_candidates.sh`. Intended-deployment checks, writer and permission inventory, a real no-match decision, existing-data bootstrap, and cutover are out of scope and were not performed.

## What Was Verified

The three approved cases exercised one generic mechanism. Cross-cutting behaviors verified across them:

- **Approved-bind without minting.** An approved existing identity returns its stored tracked UUID and identity value; retry reuses both; a conflicting value is rejected. No new identity is created.
- **Allocation idempotency.** A new tracked identity returns one UUID and one non-null identity value; retry (and changed-payload reuse) returns the same pair without minting a second.
- **Same-source serialization.** Concurrent requests for one source reuse one identity; concurrent requests for distinct sources receive distinct values.
- **Proposed-binding conflict.** An unresolved proposed binding blocks resolution and binding without advancing the allocator.
- **Required-row insertion paths.** Site and `site_location` (whose key is obtained outside SIMS), and the sample `submission → dataset → sample → analysis_entity` path, pass rollback-only Inline INSERT and copy-CSV checks.

### Historical cases (approved 2026-10-02)

| Entity | Operation | Note |
| --- | --- | --- |
| `site` | Bind an approved existing match | Weak disposable candidate (`Göteborg Raä 66`, `site_id=173`); source-target correctness not established. |
| `site` | Allocate after an approved miss | Used a mocked miss; no real no-match decision was recorded. |
| `sample` | Allocate | Required references and the required sample path verified; optional sample children excluded. |

## Where The Remaining Work Lives

- Generic capability publication, strict rejection of unconfigured operations, and batch idempotency: Phase 1 of the [phase plan](./SIMS_IDENTITY_ALLOCATION_PHASE_PLAN.md).
- Model-driven planning, capability preflight, and artifact generation: Phases 2–3.
- Existing-data bootstrap, competing-writer retirement, deployment validation, and cutover: separate operational work in the [cutover and deployment proposal](../CUTOVER_AND_DEPLOYMENT/CHANGE_REQUEST_INGESTER_CUTOVER_AND_DEPLOYMENT_PROPOSAL.md).

The SEAD table, column, sequence, and bootstrap observations that earlier versions of this guide recorded described only the disposable setup. They were retired with the contract change that scopes SIMS uniqueness to its own identity store; they do not assign SEAD integrity or schema-mapping responsibility to SIMS.
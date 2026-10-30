# Reliable Reconciliation Links to Existing SEAD Entities — Phase Plan

Source proposal: [RECONCILIATION_MVP.md](RECONCILIATION_MVP.md) (Shape Shifter). Companion proposal: [Verify Reconciliation Candidates and Match Readiness](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) (Authority Service). Related prerequisite: [Adopt Existing `site` Rows into SIMS as `materialized`](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_EXISTING_SITE_ADOPTION.md). Advice that shaped both proposals: [RECONCILIATION_MVP_REVIEW.md](RECONCILIATION_MVP_REVIEW.md).

## Summary

This plan sequences the reconciliation MVP for the entity type `site` into seven phases across two repositories. Three Shape Shifter phases (1 to 3) need no Authority Service change and deliver key-correct, owner-tagged, idempotent links with offline normalization. One Authority Service phase (4) adds the read-only candidate check, readiness check, and the SIMS binding rule. Later phases add the export check (5), the ingester rule (6), and end-to-end validation (7).

Acceptance criteria are cited by repository prefix: `SS-AC-n` for Shape Shifter and `AS-AC-n` for the Authority Service. The `P-AC-n` source column in each phase maps to these IDs. The proposals are drafts; this plan assumes their current decisions.

## Problem

Reconciliation results are not reliable today. Decisions are keyed by search label, only 1,000 rows are processed, the UI and backend disagree on the decision format, reruns can overwrite operator decisions, exported links have no owner and are never cleaned up, and the change-request ingester can pass an unreviewed fuzzy candidate to SIMS. The Authority Service has no read-only way to check a candidate, and its `site` match path failed in the one environment assessed.

## Scope

This plan covers:

- Shape Shifter backend, UI, sidecar, and ingester changes for `site`.
- Authority Service changes: candidate check, readiness check, SIMS `materialized` rule at binding, and OpenRefine fixes.
- End-to-end validation across both services.

It does not cover:

- Entity types other than `site`.
- Auto-accept of candidates.
- Live verification during normalization.
- SEAD cutover or competing-writer coordination.
- The SIMS adoption work itself, which has its own proposal and an unnamed owner. This plan treats it as a prerequisite for Phase 7.
- Staffing, dates, or release scheduling.

## Current Position

Verified in current code or configuration:

- A sidecar `Link` has no `owner` field and ignores unknown fields, so an optional new field is compatible.
- Normalization applies committed sidecar links offline, with precedence manual, reconciliation, import.
- The target-entity resolver reads entity output rows with `limit=1000`. Export writes the raw source value as the key.
- The mapping-link `PUT` endpoint stores a manual link under the project lock.
- The deployment runs one backend worker.
- The ingester treats any non-empty `public_id` as a reference to an existing entity and has its own candidate-picking adapter.
- The Authority Service has no candidate check or readiness endpoint. `/reconcile` and `/identity` have no application-level authentication.
- SIMS does not filter approved-ID resolution by lifecycle state.
- The `site` ID allocator and tracked identities for existing rows require separate adoption work.

Reported in the assessment and not re-verified: the UI and backend decision-format mismatch, and the inconsistent confidence scale. Observed in one local environment only: `authority.fuzzy_site` was missing.

## Phase Plan

### Phase 1: Key-Correct Decisions and Full Coverage

**Goal**

Store one decision per row, identified by the entity's ordered business key, for every row of the entity.

**Focus**

- Resolve all normalized rows of the entity, not the first 1,000, with progress reporting and no silent truncation.
- Store decisions by encoded `local_key`, including compound keys; report missing, duplicate, or ambiguous keys.
- Store proposed, accepted, rejected, and local-only decisions; matching only proposes.
- Make reruns refresh `proposed` rows only and never change an operator decision.
- Add a catalog format version; ignore an old-format catalog without error.

**Depends On**

- Repository current state only. No Authority Service change.

**Outputs**

- A decision store keyed by business key that later phases read for export, UI, and ingester rules.

**Acceptance Criteria**

- `PH1-AC-1` (from `SS-AC-2`) Every row is considered, including beyond 1,000 rows, and each decision uses the ordered business key, including compound keys.
- `PH1-AC-2` (from `SS-AC-2`) Two rows with the same label keep separate decisions; missing or duplicate keys are reported for the affected rows.
- `PH1-AC-3` (from `SS-AC-3`) A rerun never changes an accepted, rejected, or local-only decision, and no candidate is accepted without an operator action.
- `PH1-AC-4` (from `SS-AC-4`) An old-format catalog is ignored without error and its rows can be re-reconciled.

**Validation Milestones**

- `VM-1` Tests with duplicate labels, compound keys, and more than 1,000 rows show correct per-key decisions (`PH1-AC-1`, `PH1-AC-2`).
- `VM-2` A rerun after operator decisions leaves every decision unchanged (`PH1-AC-3`).
- `VM-3` An old-format catalog loads without error and is ignored (`PH1-AC-4`).

**Task-Plan Handoff**

- Source criteria: `SS-AC-2`, `SS-AC-3` (persistence and rerun parts), `SS-AC-4` (catalog part).
- Fixed decisions: reconcile normalized output rows, not raw rows; no auto-accept; no catalog migration; `site` is the pilot type.
- Constraint: keep the two-store design; a catalog match is not an applied link.

**Readiness**

Ready for a task plan.

### Phase 2: Review View Contract and Manual Links

**Goal**

Let the operator accept, reject, mark local-only, and add manual links through a UI that matches the backend.

**Focus**

- Make the UI send and receive the same typed decision body the backend declares; keep candidate lists on preview reload.
- Show candidates and confidence on one scale, and show failures, unresolved rows, and unverified links.
- Add manual link entry through the existing mapping-link endpoint as `source: manual`, including for entities with fixed values; do not edit fixed rows.
- Show the sidecar ID as the effective ID for a key that has a sidecar link.

**Depends On**

- Phase 1 decision store.

**Outputs**

- A working review view that later phases extend with export and verification status.

**Acceptance Criteria**

- `PH2-AC-1` (from `SS-AC-3`) The UI persists accept, reject, local-only, and manual decisions and shows candidates and confidence on one scale.
- `PH2-AC-2` (from `SS-AC-3`) The UI reports failures and unresolved rows to the operator.
- `PH2-AC-3` (from `SS-AC-3`) A manual link on a `type: fixed` entity survives a fixed-row save that does not change that key's ID, is applied by normalization over the row's own ID, and is replaced only when that key's row ID is edited.

**Validation Milestones**

- `VM-4` UI and backend tests for each decision action, with the UI request body accepted by the backend (`PH2-AC-1`, `PH2-AC-2`).
- `VM-5` A test on a `type: fixed` entity shows the manual-link behavior in `PH2-AC-3`.

**Task-Plan Handoff**

- Source criteria: `SS-AC-3`.
- Fixed decisions: manual links are trusted and not checked by the Authority Service; they are never removed by cleanup.
- Constraint: the decision-format mismatch and confidence scale were reported, not re-verified; the task plan must confirm them first.

**Readiness**

Ready for a task plan.

### Phase 3: Owned Export, Cleanup, and Offline Normalization

**Goal**

Export decisions as owner-tagged sidecar links that can be removed safely, and keep normalization offline and unchanged.

**Focus**

- Add optional `owner` `(entity_name, target_field)` and `verified_at` fields to `Link`.
- Export by encoded `local_key`; reconcile only that owner's links against its current accepted decisions.
- Remove a specification's owned links when the specification is deleted, and report the count.
- Stop export on two specifications claiming one key; treat unowned links as manual.
- Confirm normalization needs no network call and keeps its precedence.

**Depends On**

- Phase 1 decision store.

**Outputs**

- Owner-tagged links with an empty `verified_at` field that Phase 5 fills in.

**Acceptance Criteria**

- `PH3-AC-1` (from `SS-AC-4`) Export records `owner` on each reconciliation link and removes only that owner's stale links, including on specification delete.
- `PH3-AC-2` (from `SS-AC-4`) Export never removes manual or unowned links and stops on conflicting owners.
- `PH3-AC-3` (from `SS-AC-6`) Normalization applies committed links with no network call and unchanged precedence, and repeated runs give the same `public_id` values.

**Validation Milestones**

- `VM-6` Re-export after a rejection, a specification delete, and two conflicting specifications behaves as stated (`PH3-AC-1`, `PH3-AC-2`).
- `VM-7` A normalization run with no network access gives identical `public_id` and foreign-key values on repeated runs (`PH3-AC-3`).

**Task-Plan Handoff**

- Source criteria: `SS-AC-4`, `SS-AC-6`.
- Fixed decisions: cleanup on specification delete; unowned links treated as manual; keep atomic, version-checked sidecar writes; one backend worker.
- Constraint: in this phase export writes no link for a local-only decision. Phase 6 may extend export once the local-only question is decided.

**Readiness**

Ready for a task plan.

### Phase 4: Authority Service — Readiness, Candidate Check, and SIMS Binding Rule

**Goal**

Give consumers a read-only check that a `site` candidate exists in SEAD, a real readiness check, and a SIMS rule that binding needs a `materialized` identity.

**Focus**

- Confirm the database-backed `site` match path works; fix or report the missing `authority.fuzzy_site` dependency.
- Add `POST /reconcile/verify-candidates` and `GET /reconcile/readiness` with the formats, status codes, and 100-item limit fixed in the Authority proposal.
- Validate candidate URIs inside the service and gate types by configured strategy and `bind_existing`.
- Make `POST /identity/resolve` reject non-`materialized` approved identities, including through an existing binding, checked in the same transaction.
- Honor the per-query `limit` and return a client error for an unsupported type.

**Depends On**

- None in Shape Shifter. The `site` database-backed match path must be confirmed within this phase.

**Outputs**

- A working candidate check and readiness endpoint for Phase 5, and the binding rule for Phase 7.

**Acceptance Criteria**

- `PH4-AC-1` (from `AS-AC-1`, `AS-AC-2`) One batch returns one ordered result per candidate; only a valid candidate with an existing SEAD row is `exists`; invalid candidates are `invalid_candidate`; a type without `bind_existing` is `unsupported_type`.
- `PH4-AC-2` (from `AS-AC-3`) A SEAD database failure fails the operation with HTTP 503, and the check performs no identity or binding writes.
- `PH4-AC-3` (from `AS-AC-4`) `GET /reconcile/readiness` reports not ready with a reason when a required match dependency is missing, while `GET /reconcile` keeps serving metadata.
- `PH4-AC-4` (from `AS-AC-5`) `POST /identity/resolve` rejects non-`materialized` approved identities and checks state in the same transaction as the binding.
- `PH4-AC-5` (from `AS-AC-7`) A validated per-query `limit` is honored and an unsupported type returns a client error, with existing formats unchanged.

**Validation Milestones**

- `VM-8` Disposable-database tests for `site` cover existing, missing, mismatched, and invalid candidates, database outage, and absence of writes (`PH4-AC-1`, `PH4-AC-2`).
- `VM-9` Readiness fails with a reason on a database missing the match function (`PH4-AC-3`).
- `VM-10` Binding tests cover each non-`materialized` state, an existing binding, and a state change between lookup and binding (`PH4-AC-4`).
- `VM-11` OpenRefine request and response compatibility tests pass (`PH4-AC-5`).

**Task-Plan Handoff**

- Source criteria: `AS-AC-1` to `AS-AC-5`, `AS-AC-7`. `AS-AC-6` is covered by the validation milestones here and by Phase 7.
- Fixed decisions: endpoint names, formats, status codes, and batch limit in the Authority proposal; no new authentication; SIMS never reads SEAD.
- Constraint: Phase 5 needs only `PH4-AC-1` to `PH4-AC-3`. The task plan should deliver the candidate check and readiness before the binding rule and OpenRefine fixes.
- The task plan belongs in the Authority Service repository.

**Readiness**

Ready for a task plan.

### Phase 5: Export Verification

**Goal**

Check at export that each accepted candidate exists in SEAD, and show the result to the operator.

**Focus**

- Send accepted candidates to the Authority Service candidate check at export; Shape Shifter does no URI parsing.
- On `exists`, export with `verified_at` set; on `not_found` or `invalid_candidate`, do not export and tell the operator why.
- When the service is unavailable, export with `verified_at` empty and show the link as unverified.

**Depends On**

- Phase 3 owned export.
- Phase 4 candidate check and readiness (`PH4-AC-1` to `PH4-AC-3`).

**Outputs**

- Links that carry a verification result for the operator.

**Acceptance Criteria**

- `PH5-AC-1` (from `SS-AC-5`) A candidate the service reports as absent or invalid is not exported, and the operator sees the reason.
- `PH5-AC-2` (from `SS-AC-5`) An unavailable service results in an exported link with empty `verified_at`, shown as unverified, and a later re-export can verify it.

**Validation Milestones**

- `VM-12` Tests against a disposable service cover `exists`, `not_found`, `invalid_candidate`, and an unavailable service (`PH5-AC-1`, `PH5-AC-2`).

**Task-Plan Handoff**

- Source criteria: `SS-AC-5`.
- Fixed decisions: export is the only live check; manual links are not checked; the check is read-only.

**Readiness**

Ready for a task plan, once Phases 3 and 4 have delivered their outputs.

### Phase 6: Change-Request Ingester Rule

**Goal**

Make the change-request ingester resolve existing entities only through sidecar links and block unreconciled rows.

**Focus**

- Stop the ingester's own candidate picking; never pass an unreviewed candidate to SIMS.
- Resolve an existing entity only when normalization set its `public_id` from a sidecar link.
- Block, not allocate, a row of a reconciled entity that has no operator decision.
- Decide how a local-only decision reaches the ingester, and extend export if needed.

**Depends On**

- Phase 1 decision store.
- Phase 3 owned export.
- Decision: how a local-only decision reaches the ingester (proposal open question).

**Outputs**

- An ingester that cannot create duplicate entities from unreconciled rows.

**Acceptance Criteria**

- `PH6-AC-1` (from `SS-AC-7`) The ingester does not select or pass an unreviewed candidate to SIMS.
- `PH6-AC-2` (from `SS-AC-7`) A row resolves to an existing entity only through a sidecar link, and a row of a reconciled entity without an operator decision is blocked, not allocated.

**Validation Milestones**

- `VM-13` Ingester tests cover a link-resolved row, a pre-linked ID, and an unreconciled row, for each reconciliation mode that applies to `site` (`PH6-AC-1`, `PH6-AC-2`).

**Task-Plan Handoff**

- Source criteria: `SS-AC-7`.
- Fixed decisions: the ingester does not read `verified_at`; no current project relies on its candidate picking; SIMS enforces tracked identity at binding.
- Blocking question: can a sidecar link without a target carry a local-only decision, and how does it interact with `lookup-only`, `lookup-extensible`, `reconcile-exact`, and `reconcile-fuzzy`? This can change both the export format and the ingester tests.

**Readiness**

Requires a named decision: how a local-only decision reaches the ingester.

### Phase 7: End-to-End Validation

**Goal**

Prove the full workflow for `site` against real services, including repeated runs.

**Focus**

- Run review, export, normalization, and change-request generation against a disposable database-backed reconciliation service and SIMS.
- Confirm actual `public_id` and downstream foreign-key values for accepted and rejected cases.
- Confirm a health-only service cannot pass readiness.

**Depends On**

- Phases 2, 5, and 6 outputs, and Phase 4 binding rule.
- SIMS adoption of existing `site` rows (separate proposal; owner not yet named).

**Outputs**

- A validation record for the MVP.

**Acceptance Criteria**

- `PH7-AC-1` (from `SS-AC-1`) A reviewed `site` workflow sets the intended `public_id` and foreign-key values, and rerunning review, export, and normalization without changes gives identical results.
- `PH7-AC-2` (from `SS-AC-8`) One end-to-end test covers the success path and the rejection, rerun, changed-decision, stale-link, absent-row, and unavailable-service cases.
- `PH7-AC-3` (from `SS-AC-8`, `AS-AC-6`) A health-only service cannot pass readiness, and an approved existing `site` binds through SIMS after adoption.

**Validation Milestones**

- `VM-14` The end-to-end run records actual target IDs and foreign-key values for accepted and rejected cases (`PH7-AC-1`, `PH7-AC-2`).
- `VM-15` Readiness fails against a health-only or incomplete service, and a binding succeeds after adoption (`PH7-AC-3`).

**Task-Plan Handoff**

- Source criteria: `SS-AC-1`, `SS-AC-8`, `AS-AC-6`.
- Blocking question: who owns and schedules the SIMS adoption of existing `site` rows? Without it, existing-site binding cannot be validated.

**Readiness**

Requires a named decision: an owner for the SIMS adoption work.

## Cross-Phase Rules

- Phases 1 to 3 and Phase 4 can proceed in parallel; Phases 5 and 6 wait on the outputs listed in their dependencies.
- Normalization stays offline. The only live check is at export.
- The Authority proposal is the normative contract. Shape Shifter code must not restate candidate URI rules.
- `site` is the only pilot type. Do not generalize to other types before Phase 7 passes.
- No auto-accept. A catalog match is not an applied link.
- Keep the two-store design, manual-link precedence, `system_id` relationships, and version-checked sidecar writes.
- Keep one backend worker per project data directory.
- Update this plan and the proposals together when a decision changes.

## Validation Strategy

- **Unit and API tests:** per-phase contracts for keys, decisions, export, the candidate check, readiness, and the binding rule.
- **UI tests:** decision actions and manual links in Phase 2.
- **Disposable database-backed tests:** Authority phase and Phase 5, using a real `site` match request, not only health or manifest checks.
- **End-to-end run:** Phase 7 across both services and SIMS, checking actual target IDs and foreign-key values.
- Each phase's expected results are in its validation milestones. Exact commands, test files, and fixtures belong in the task plans.

## Final Recommendation

Start Phases 1, 2, 3, and 4 now: they are ready for task plans and have no open decision. Resolve the local-only decision before Phase 6 and name an owner for the SIMS adoption work before Phase 7. Do not call the workflow an MVP until Phase 7 passes.

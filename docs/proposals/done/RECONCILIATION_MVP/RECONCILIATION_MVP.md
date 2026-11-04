# Reliable Reconciliation Links to Existing SEAD Entities

## Status

- **Implemented** (branch `reconciliation-mvp`; not yet merged).
- Scope: A human-reviewed workflow that links normalized rows to existing SEAD entities, with links that stay correct across reruns. Delivered for the entity type `site` only.
- Goal: Make an exported reconciliation decision reliably set the intended row's `public_id`, and make every rerun of the workflow produce the same result.
- Validation: Recorded in the [phase plan](RECONCILIATION_MVP_PHASE_PLAN.md) task plans. Phase 7 end-to-end validation passed on 2026-10-31 against a helper-owned disposable database and a live Authority Service: 5 tests passed with zero skips, binding adopted `site_id` 1, allocating local-only `site_id` 6504, generating `sample_group_id` 13962, and keeping the Core child FK on local `system_id` 10001. The Phase 7 manual UI review passed on 2026-11-04. Phase 4, the Authority Service candidate, readiness, and SIMS binding work, is tracked in the companion Authority Service proposal, not in this repository.
- Remaining follow-up: Merging the implementation; extending the workflow beyond `site` is tracked by [RECONCILIATION_ENTITY_TYPE_EXPANSION](../../RECONCILIATION_ENTITY_TYPE_EXPANSION/RECONCILIATION_ENTITY_TYPE_EXPANSION.md).

## Summary

Reconciliation is a qualitative task with an operator in the loop. The matching service suggests candidates and the operator decides. This proposal keeps the existing reconciliation catalog and the explicit export to the mapping sidecar, and fixes what makes the result unreliable today: decisions are stored by search label instead of business key, only 1,000 rows are processed, review actions do not match the backend, reruns can overwrite operator decisions, and exported links have no owner and are never cleaned up.

The design rests on the three-tier identity system. A decision identifies a row by its `keys` (business key), which stay the same between runs. An accepted existing-entity decision supplies the row's `public_id`; an exported local-only decision authorizes new-ID allocation during change-request generation. The local `system_id` is never stored in a decision. Exporting the same decisions and normalizing the same data produce the same links and `public_id` values.

Normalization stays offline and unchanged: it applies committed sidecar links without calling any service. The one live check is a read-only test, run at export, that the chosen candidate still exists in SEAD. SIMS rules for existing IDs stay where they are enforced today: at SIMS resolve and bind during change-request generation.

The [status assessment](RECONCILIATION_MVP_ASSESSMENT.md) records current behavior. The companion [Authority Service proposal](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/RECONCILIATION_IDENTITY_CONTRACT/RECONCILIATION_IDENTITY_CONTRACT.md) is the single normative definition of the candidate check this proposal calls.

## Problem

Shape Shifter can export a resolved ID and apply it during normalization when the reconciled field is also the sidecar's local key. It cannot guarantee that the ID belongs to the intended row, that it still exists in SEAD, or that a rejected decision is removed from the sidecar.

- Query results are stored by search-field value, but normalization matches by the sidecar's business key. Two rows with the same label but different keys can share or overwrite a decision.
- The default entity-preview resolvers return at most 1,000 rows.
- The UI submits JSON bodies for manual decisions, but the backend declares those parameters as query parameters. Preview reload drops candidate lists, and confidence is shown on inconsistent scales.
- Reruns can replace operator decisions, and re-export does not remove a link rejected after an earlier export.
- A sidecar `Link` records `source: reconciliation` but not which specification wrote it, so stale links cannot be removed safely.
- The change-request ingester picks the top fuzzy candidate without requiring `match=true` and passes it to SIMS. A row that already has a `public_id` skips that path entirely.
- A missing `public_id` does not distinguish an operator-approved new entity from a row that has not been reviewed; the ingester's normalized-table input carries no decision metadata.

## Scope

- Deliver one pilot workflow end to end for the entity type `site`.
- Reconcile the complete set of normalized rows for an entity, with each decision identified by the entity's ordered business key (the sidecar `local_key`), including compound keys.
- Store proposed, accepted, rejected, and local-only decisions; matching only proposes, and every link needs an operator action.
- Let the operator enter a link manually (key and target ID), for example for entities with fixed values.
- Export with a specification owner and a verification timestamp on each reconciliation link, and remove only that owner's stale links.
- Check at export that the candidate exists in SEAD, using the Authority Service.
- Make the change-request ingester use exported links for existing IDs and exported local-only approvals for new-ID allocation.
- Show failures, unresolved rows, and unverified links to the operator.

## Non-Goals

- Support for entity types other than `site` in the first MVP.
- Automatic acceptance of candidates, score thresholds, or bulk accept.
- Live verification during normalization, or any change to normalization's offline behavior.
- Migrating legacy reconciliation catalogs or links; no project uses them.
- Checking SIMS lifecycle state from reconciliation, or adopting existing SEAD rows into SIMS. SIMS enforces its own rules when a change request binds an ID.
- Audit history, multi-reviewer approval, or rollback; see [Reconciliation Future Improvements](../../RECONCILIATION_FUTURE_IMPROVEMENTS.md).
- Changing the three-tier identity model, Core foreign keys, or the Extract → Filter → Link → Unnest → Translate → Store order.
- Replacing the fixed-entity mapping synchronization.

## Current Behavior

- Results are saved in a reconciliation catalog; only exported links in the sidecar affect normalization. Export protects manual sidecar links, and normalization applies committed links to `public_id` using the order manual, reconciliation, import ([export](../../../../backend/app/services/reconciliation/service.py#L217), [normalization](../../../../src/normalizer.py#L536)).
- `Link` has fields for source, target ID, confidence, timestamps, notes, and reviewers, but no owner. It does not set a Pydantic `extra` mode, so unknown fields are ignored by default; an optional new field is compatible with existing sidecars (verified in [sidecar model](../../../../src/reconciliation/mapping_model.py#L143)).
- The target-entity resolver reads the entity's output rows through the preview service with `limit=1000`. Export writes the raw reconciliation source value as the sidecar key instead of the `local_key` ([resolvers](../../../../backend/app/services/reconciliation/resolvers.py#L72), [export](../../../../backend/app/services/reconciliation/service.py#L237)).
- UI and backend disagree on the manual-decision request format, and confidence is displayed inconsistently ([routes](../../../../backend/app/api/v1/endpoints/reconciliation.py#L423), [view](../../../../frontend/src/components/reconciliation/ReconciliationView.vue#L254), [grid](../../../../frontend/src/components/reconciliation/ReconciliationGrid.vue#L400)). These were reported in the assessment and not re-verified for this revision.
- The ingester adapter selects a top candidate without a threshold or `match=true` ([adapter](../../../../backend/app/services/ingester_runtime.py#L320), [planning](../../../../ingesters/sead_change_request/planning.py#L96)).
- The ingester's normalized-table bundle has no operator-decision metadata, and a missing `public_id` is planned as reconciliation work ([bundle](../../../../ingesters/sead_change_request/contracts.py#L84), [planning](../../../../ingesters/sead_change_request/planning.py#L28)).
- In the assessed local environment, a real `site` reconciliation request returned HTTP 500 because `authority.fuzzy_site` was missing. This is an environment-specific observation.
- No `source: reconciliation` links were found under `data/projects`.

## Proposed Design

### Source rows, keys, and decisions

Reconciliation works on the normalized output of the entity, not on raw source rows. Each row is identified by the entity's ordered `local_key`. The query label and other properties are used only to find candidates.

- Process every row, not only the first 1,000. Report progress and never truncate silently.
- Report missing, duplicate, or ambiguous keys as errors for the affected rows instead of merging them.
- Store decisions by encoded `local_key`. Two rows with the same label keep separate decisions.
- Store each decision as proposed, accepted, rejected, or local-only. Matching only creates `proposed`. An operator action is required to accept, reject, or mark local-only.
- A rerun may refresh candidates for `proposed` rows. It never changes an accepted, rejected, or local-only decision.
- Use one confidence scale (0 to 1 internally, shown as a percentage) in the UI.
- The catalog gets a format version. A catalog in the old format is ignored and its rows are re-reconciled; there is no migration.

The UI sends and receives the same typed decision body that the backend declares, and keeps candidate lists when it reloads the preview.

### Manual links

An operator can add a link by entering the key and the target ID in the review view, including for entities with fixed values.

- The view writes the link through the existing mapping-link endpoint (`PUT /projects/{project}/mapping/{entity}/{key}`), which stores it as `source: manual` under the project lock. It does not edit the fixed row.
- A manual link is never removed by cleanup and takes precedence over reconciliation links, as in normalization today.
- A manual entry is a bare integer, not a candidate URI, so the Authority Service check does not run on it. It is trusted and shown as manual and not verified.
- Fixed-row save sync changes only keys whose row ID changed, so it does not overwrite a manual link until someone edits that row's ID. In that case the last writer wins, as today.
- For a key with a sidecar link, the view shows the sidecar ID as the effective ID, because normalization applies the sidecar first.

### Export and ownership

Explicit export remains the point where decisions become committed sidecar entries.

- Each exported reconciliation link records its owner, the pair `(entity_name, target_field)`, as a new optional `owner` field, and `verified_at`, the time the SEAD check passed (empty when not verified).
- Export reconciles only that owner's links against its current accepted decisions. A rejected or removed decision removes its previously exported link.
- Deleting a specification also removes its owned links in the same operation, and the response reports how many were removed.
- If two specifications claim the same sidecar key, export stops and reports the conflict.
- A link without an owner (hand-edited or created before this change) is treated like a manual link: cleanup never removes it, and normalization still applies it.
- Keep atomic, version-checked sidecar writes and the current fixed-row synchronization.

A local-only decision exports an owner-tagged approval in the sidecar, keyed by the same encoded business key but stored separately from ID links. It is not a `Link` with `target_id: null`: committed links still mean "use this existing ID." Re-export removes stale approvals belonging to that specification when decisions change or disappear; deleting the specification removes its approvals. Export stops on conflicting owners or a conflicting manual or unowned link for the same key, without deleting that link. A rejected or removed decision exports neither an ID link nor an allocation approval.

### Verification at export

At export, Shape Shifter sends each accepted candidate to the Authority Service candidate check defined in the companion proposal. The service parses the candidate ID, rejects a wrong origin, type, or shape, and reports whether the SEAD row exists. Shape Shifter does not parse candidate URIs itself.

- Check passes: the link is exported with `verified_at` set.
- Check reports the row is absent or the candidate invalid: the link is not exported, and the operator is told why.
- Service unavailable: the link is exported with `verified_at` empty, marked `unverified` in the UI, and the operator can re-export later to verify it.

The check is read-only. It does not bind, allocate, or write any SIMS state.

### Normalization

No change to ID assignment. Normalization applies committed ID links offline from the sidecar, in the existing precedence order, with no network call. Local-only approvals do not write a null target ID to `public_id` or add an approval column to the data. A run with the same sidecar and data gives the same `public_id` values every time.

### Change-request ingester

- The backend supplies approvals from the authorized project's committed sidecar to the ingester as trusted metadata alongside normalized tables. A catalog decision that has not been exported does not authorize allocation.
- The ingester's own lookup no longer approves a match. It never takes the top fuzzy candidate and never passes an unreviewed candidate to SIMS. Normalization supplies existing IDs from sidecar links; a missing ID alone never authorizes allocation.
- A reconciled row with no ID and no exported local-only approval is blocked, whether its decision is rejected or still undecided. An explicit local-only approval may allocate with `reconcile-exact` or `reconcile-fuzzy`; `lookup-only` and `lookup-extensible` never allocate through this ingester. A pre-linked ID conflicting with a local-only approval is blocked rather than silently allocated.
- The ingester does not read `verified_at` or the decision catalog. SIMS enforces tracked identity when it binds an existing ID. Unverified links are visible in the review UI and the export result instead.
- Pre-linked IDs are referenced as existing IDs through the current path. This proposal adds no provider binding for reference-only imports.

## Alternatives Considered

- **Verify live at normalization (earlier draft):** Rejected. It makes normalization depend on network services, breaks offline and CI runs, and duplicates the export check.
- **Check SIMS `materialized` state during reconciliation:** Deferred. Existing SEAD rows are not adopted into SIMS and no adoption work is planned, so every candidate would be ineligible. SIMS already enforces its rules at binding.
- **Auto-accept high-scoring candidates:** Rejected for the MVP. Scores rank candidates but cannot disambiguate equal labels or preserve rejections, and thresholds add rules without removing the need for review.
- **Limit MVP to fields that equal the business key:** Cannot link entities found by a different label or tell duplicate names apart.
- **Replace the two stores with one now:** Broadens migration risk; correct alignment of the current stores addresses the decision.
- **Use a targetless sidecar link for local-only:** Rejected. Normalization writes a committed link's `target_id` into `public_id`; a null target could erase an existing ID, while the ingester still could not distinguish approval from an undecided row.

## Risks And Tradeoffs

- **Unverified links:** Export succeeds when the Authority Service is down, so a link can be exported without a check. The `unverified` mark in the UI and export result limits the effect, and SIMS enforces tracked identity when the ID is bound. A SEAD row removed after export is not detected until re-export.
- **Stale links:** A SEAD row can disappear after export. Normalization does not detect this. SIMS binding catches untracked or invalid IDs, but SEAD row removal is detected only by a later re-export.
- **Existing-data adoption:** Importing a reconciled existing `site` through SIMS requires its row to be tracked in SIMS. That adoption has no plan or owner (see Open Questions). Reconciliation links can be created without it, but the change-request step will fail on untracked IDs.
- **Volume:** Processing all rows costs more than a 1,000-row preview. Use batching and progress reporting.
- **Concurrency:** The project lock is process-local. The deployment runs one backend worker, which [OPERATIONS.md](../../../OPERATIONS.md) already requires and the container `CMD` enforces with `--workers 1`. This proposal adds no cross-process locking and depends on that constraint; revisit only if multi-worker deployment is planned ([mapping sync status](../../done/MATERIALIZED_ENTITY_MAPPING_SYNC/MATERIALIZED_ENTITY_MAPPING_SYNC.md)).
- **Manual links:** They are trusted and not checked against SEAD, so a typo in a target ID is not detected. SIMS enforces tracked identity when the ID is bound.
- **Allocation approvals:** Exported local-only approvals add a separate sidecar entry and trusted ingester input. Export must prevent conflicting ownership and links, and the ingester must reject missing or inconsistent approval metadata rather than treating an unreviewed row as an allocation miss.

## Testing And Validation

Use focused Core, API, UI, and ingester tests, plus an end-to-end run against a disposable database-backed reconciliation service. Cover:

- distinct business keys that share a search label, and compound keys
- more than 1,000 rows
- accept, reject, local-only, and manual actions, and a rerun that preserves them
- a manual link on a `type: fixed` entity: it survives a fixed-row save that does not change that key's ID, is applied by normalization over the row's own ID, and is replaced only when that key's row ID is edited
- re-export after a rejection, a change between accepted and local-only, a specification delete, and with two conflicting specifications
- unowned and manual links surviving cleanup
- exported local-only approvals being removed when stale, and conflicts with a pre-linked ID or a manual link being blocked
- a candidate reported as absent or invalid, and an unavailable service at export
- normalization with no network access producing the same `public_id` and downstream foreign-key values on repeated runs
- change-request generation with a link-resolved row, a pre-linked ID, an approved local-only row, a rejected row, and an undecided row; test all four reconciliation modes so only an approved `reconcile-exact` or `reconcile-fuzzy` row may allocate

Verify actual target IDs and downstream foreign-key values, not only HTTP responses or link counts. Test the service with a real match request, not only health or manifest checks.

## Acceptance Criteria

- `SS-AC-1` For entity type `site`, a reviewed match-to-import workflow runs against a real database-backed service, and normalization sets the intended `public_id` and downstream foreign-key values. Rerunning review, export, and normalization without changes gives identical results.
- `SS-AC-2` Every row is considered, including beyond 1,000 rows. Each decision, exported link, and local-only approval uses the ordered business key, including compound keys. Duplicate labels never share a decision. Missing or duplicate keys are reported.
- `SS-AC-3` The UI persists accept, reject, local-only, and manual decisions, shows candidates and confidence on one scale, and reports failures and unresolved rows. Reruns never change an operator decision. No candidate is accepted without an operator action.
- `SS-AC-4` Export records `owner` and `verified_at` on each reconciliation link and owner on each separate local-only approval. It removes only that owner's stale links and approvals (including on specification delete), never removes manual or unowned links, and stops on another owner's claim or a conflicting manual or unowned link. An old-format catalog is ignored without error.
- `SS-AC-5` At export, a candidate the Authority Service reports as absent or invalid is not exported; an unavailable service results in an exported link with empty `verified_at`, shown as unverified.
- `SS-AC-6` Normalization applies committed links with no network call and unchanged precedence.
- `SS-AC-7` The change-request ingester does not select or pass an unreviewed candidate to SIMS. Existing-ID links set `public_id`, pre-linked IDs keep their existing path unless an approval conflicts, and rejected or undecided reconciled rows without an ID are blocked. Only exported local-only approvals passed as trusted metadata may allocate, and only with `reconcile-exact` or `reconcile-fuzzy`; `lookup-only` and `lookup-extensible` never allocate.
- `SS-AC-8` A disposable, database-backed end-to-end test covers the success path and the local-only approval, undecided-row block, rejection, rerun, changed-decision, stale-link, absent-row, and unavailable-service cases. A health-only service cannot pass readiness.

## Planning Handoff

**Confirmed decisions**

- Pilot type is `site`. The `site` database-backed match path must work before review and export are promoted (see the companion proposal's readiness check).
- Normalization stays offline. The only live check is at export. SIMS state is not checked by reconciliation.
- No auto-accept. Matching only proposes.
- No legacy migration. Old-format catalogs are ignored. Links without an owner are treated like manual links.
- Cleanup of a removed specification runs when the specification is deleted.
- Manual links, including for fixed-valued entities, go through the existing mapping-link endpoint as `source: manual`, are not checked by the Authority Service, and do not edit fixed rows.
- No cross-process sidecar locking. One backend worker per project data directory is a deployment constraint, already stated in [OPERATIONS.md](../../../OPERATIONS.md).
- Exported local-only approvals are distinct from ID links, keyed and owned by specification, and passed from the authorized sidecar as trusted ingester metadata. A missing `public_id` alone never permits allocation.
- The change-request ingester does not read `verified_at` or pick candidates. It uses sidecar links for existing IDs, keeps the pre-linked-ID path, blocks rejected and undecided reconciled rows without IDs, and permits approved allocation only for `reconcile-exact` and `reconcile-fuzzy`. No current project relies on its own candidate picking.
- The Authority Service proposal is the single normative contract; this proposal does not restate candidate URI rules.
- Acceptance criteria use the `SS-AC-` prefix here and `AS-AC-` in the Authority Service proposal. This differs from the repository's usual `P-AC-` form so that phase plans can cite both documents without collisions.

**Preserve**

- Two-store design (catalog and sidecar), explicit export, manual-link precedence, Core `system_id` relationships, and version-checked sidecar writes.
- Do not equate a catalog match with an applied link.

**Phase ordering**

- Work that does not need the Authority Service can be delivered first: business-key decisions, full coverage, the UI contract, ownership, cleanup, manual links, and offline normalization (`SS-AC-2`, `SS-AC-3`, `SS-AC-4`, `SS-AC-6`).
- The export check (`SS-AC-5`) needs the Authority Service candidate check. The ingester rule (`SS-AC-7`) does not.

**Validation**

- Show actual normalized IDs and downstream references for accepted, local-only, rejected, and undecided cases, not passing counts of mocked tests.

## Open Questions

- **Existing-data adoption into SIMS for `site`:** Tracked in [Adopt Existing `site` Rows into SIMS as `materialized`](https://github.com/humlab-sead/sead_authority_service/blob/main/docs/proposals/SIMS_EXISTING_SITE_ADOPTION.md). It does not block reconciliation links but blocks end-to-end import of existing sites through SIMS. Its owner must be named before the ingester phase is validated end to end.

## Final Recommendation

Approve a small, human-reviewed MVP for `site` that fixes row identity, coverage, review persistence, and link ownership, keeps normalization offline, and adds one read-only SEAD existence check at export. Do not call the current fuzzy-search-and-export workflow an MVP until the end-to-end checks above pass.

# Handoff: Shared Data Review And Operator Contract

## Purpose

Resume work on the shared-data review proposal without replaying the full session.

## Current State

- The Change Request Ingester MVP binds existing shared lookups. Current lookup-only reconciliation blocks on a miss; it does not create a value or request.
- Post-MVP, an authorized internal operator may start a reviewable shared-data request from a reconciliation no-match. Approval, duplicate checks, and audit/provenance are required before publication.
- Normal external provider ingest must not create shared values. SIMS `allocate_new` allocates identity; it does not itself authorize publication of a shared lookup.
- `sample_group.role` is now `fact` in all three canonical target models and their test/project mirrors. `site` remains a lookup.
- Do not equate target-model `role` with SIMS ownership. The Authority Service policy classifies `site` as `shared_metadata` and `sample_group` as `provider_owned`; `sample_group` has `allocate_new: true` and `bind_existing: false`.

## Completed Work

- Consolidated post-MVP proposal documents under `CHANGE_REQUEST_INGESTER_POST_MVP`; the consolidation was committed as `b0ed9b05`.
- Changed `sample_group` from `lookup` to `fact` in the three canonical models and five corresponding test/project copies.
- Ran `rtk uv run pytest tests/target_model/test_spec_files.py tests/target_model/test_example_projects.py -q`: 18 tests passed. The role scan and `git diff --check` also passed.
- The proposal and eight model copies are currently unstaged. This handoff is a new file. The `dev` branch was six commits ahead of `origin/dev` at the last status check.

## Key References

- [Shared-data review proposal](SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md)
- [Standard target model](../../../../resources/target_models/sead_standard_model.yml)
- [Durable provider lifecycle rules](../../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)
- Authority Service identity policy: `sead_authority_service/config/identity_policy.yml` in the multi-root workspace.

## Next Actions

1. Update the proposal's stale claim that both `site` and `sample_group` have target role `lookup`. Separate `site` shared-lookup policy from `sample_group` provider-owned identity allocation.
2. Resolve whether `site.allocate_new` is disabled for the bind-existing-only MVP or allowed only through a separately approved workflow. Do not treat the capability as publication approval.
3. Specify the MVP no-match outcome. The proposal currently permits either blocking or a review outcome without defining when each applies or what the outcome means.
4. Define internal requester, approver, and publisher roles; request artifact fields; duplicate checks; provenance/audit data; and operator-visible statuses.
5. Clarify whether the future authority-backed workflow only links an existing SEAD value or requires the same review path for a new local value. Keep normal provider ingest unable to publish shared data.
6. An earlier scan found six pre-existing broken links to the durable lifecycle document in archived lifecycle records. They were not changed; recheck them if archive cleanup is in scope.

## Open Decisions

- What exact no-match status does the MVP expose, and does it vary by workflow?
- Who may request shared-data changes, and who may approve and publish them?
- What is the permitted `site` allocation behavior under the MVP policy?
- Does an authority-backed match ever create a local shared row, or only reference an existing SEAD row?

## Risks

- Treating target-model role as ownership could cause provider-owned `sample_group` identity allocation to be confused with shared lookup publication.
- Leaving `site.allocate_new` unresolved could make configured SIMS capabilities disagree with the MVP's bind-existing-only rule.
- A vague "review outcome" or authority-backed workflow could weaken the provider-ingest restriction or produce inconsistent operator behavior.
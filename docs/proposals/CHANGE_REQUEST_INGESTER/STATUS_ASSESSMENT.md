# Change Request Ingester — Proposal Status Assessment

- Status: Assessment snapshot
- Date: 2026-08-26
- Branch: `dev`
- Scope: `CHANGE_REQUEST_INGESTER` proposal set

## Overall Status

**Mature and largely complete.** The core deliverable, all accepted follow-up work, and the entire provider-lifecycle policy are implemented, tested, and merged into `dev`. What remains is a small set of well-defined open items, most of which are decision-gated rather than implementation-blocked.

## Done (verified against code, git, and tests)

| Area                                 | Evidence                                                                                                                                                                                                             |
|--------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Delivery 1 baseline                  | Closed/archived under `done/CHANGE_REQUEST_INGESTER_DELIVERY_1/` — DataFrame-first, identity resolution before SQL, SIMS allocation, reconciliation-first, forward-only non-revertible                               |
| Delivery 1 follow-ups                | Resolved — SQL rendering split, `copy_csv` artifact format, Jinja2 evaluation, target-model/schema review                                                                                                            |
| SIMS `target_id` contract            | Satisfied upstream and consumed by the ingester; local handoff docs moved to `humlab-sead/sead_authority_service:docs/proposals/` (the local `SIMS_TARGET_ID_CONTRACT*.md` files no longer exist)                    |
| Frontend UX integration (Issues 1–4) | Implemented (PR #456) — dedicated `sead_change_request` workflow, submission-context form, blocked-confirmation state, artifact outcomes. Confirmed in `frontend/src/components/ingester/IngesterForm.vue` and tests |
| Lifecycle policy gate                | Accepted, promoted to durable `docs/DATA_PROVIDER_SUBMISSION_LIFECYCLE.md`                                                                                                                                           |
| Lifecycle Phase 1 & 2                | Implemented — metadata contracts, one-live-version invariant, outcome classification (`new_data` / `no_op` / `allowed_update` / `pending_review` / `blocked`)                                                        |
| Lifecycle Phase 3                    | Implemented — existing-row update engine path, mutable-field boundaries, no-op/supersession, SQL + artifact rendering, first-slice allowlist guard                                                                   |
| Ingester readability refactor        | Done, stopped at a stable boundary                                                                                                                                                                                   |

All of this is on `dev`; `cr-ingester-final-work` is behind `dev` (empty diff for ingester paths — nothing unmerged). Targeted ingester suite passes (72 tests).

## Remaining / Blockers

1. **Deferred frontend Issue 5** — persist stable `sead_change_request` submission defaults in project YAML (ingester-specific metadata subsection). The frontend currently pre-fills defaults from the project name/description at form-open time only; nothing is persisted per-ingester. **No blocker** — needs a scope decision (which defaults: datatype, deploy strategy, issue number, author …) plus backend and frontend work.
2. **Shared-data review proposal** — draft in the separate `SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/` folder. **Blocked on ownership decisions**: who owns reviewed shared-data requests/approvals, and the boundary between provider-owned reference updates and shared-row governance. External/authority dependency.
3. **Next-delivery candidate selection** — `future/NEXT_DELIVERY_CANDIDATES.md` (rollback, stronger idempotency, change detection, precise ordering, stronger verification) is explicitly **undecided**; the tracker forbids committing a candidate until steps 1–4 are settled (they now are).
4. **Git hygiene** (minor) — `dev` is 1 commit ahead of `origin/dev` (graphify update); there are uncommitted instruction-file edits and an unrelated untracked proposal (`RULESYNC_AGENT_INSTRUCTIONS_UNIFICATION.md`).

## Proposed Next Phase: Close The Deferred Frontend Issue 5

This is the most logical next slice because it is the **only remaining open item from already-accepted scope**, it is fully within the repo's control (no external decisions), and it completes the frontend integration work so the proposal can be formally closed/archived like the lifecycle set.

### Slice Scope (narrow)

- Add an ingester-specific metadata subsection (e.g. `ingester_defaults: { sead_change_request: { datatype, deploy_strategy, … } }`) to the project YAML model plus `ProjectMapper` — `backend/app/models/project.py`, mapper, and `shapeshifter.yml` docs.
- Frontend: read the persisted defaults in `IngesterForm.vue` instead of purely deriving transient prefills (`applyIngesterDefaults`), with a clear "project default vs per-run override" distinction.
- Tests: backend model/mapper round-trip plus frontend prefill test (extend the existing `prefills project-derived submission context` test).
- Update `done/FRONTEND_UX_INTEGRATION_ISSUES.md` Issue 5 status and mark the frontend CR fully closed.

### Alternatives

- **B — Advance the shared-data proposal**: larger design work, but blocked on owner decisions that require stakeholder input.
- **C — Select one `future/NEXT_DELIVERY_CANDIDATES.md` item**: rollback is the highest-value/riskiest; idempotency is the most incremental. Portfolio decision.

## References

- Proposal README: [README.md](./README.md)
- Consolidated tracker (archived): [done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md](./done/DATA_PROVIDER_SUBMISSION_LIFECYCLE/CHANGE_REQUEST_INGESTER_STATE_AND_REMAINING_TASKS.md)
- Durable lifecycle rules: [../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md](../../DATA_PROVIDER_SUBMISSION_LIFECYCLE.md)
- Candidate backlog: [future/NEXT_DELIVERY_CANDIDATES.md](./future/NEXT_DELIVERY_CANDIDATES.md)
- Existing-row update proposal: [future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md](./future/UPDATE_HANDLING_FOR_EXISTING_ROWS.md)
- Shared-data review: [SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md](./SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT/SHARED_DATA_REVIEW_AND_OPERATOR_CONTRACT.md)

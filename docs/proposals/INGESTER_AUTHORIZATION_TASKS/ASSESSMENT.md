# Assessment: Consequences of Putting INGESTER_AUTHORIZATION_TASKS On Hold

Reviewed: [INGESTER_AUTHORIZATION_TASKS.md](../archive/INGESTER_AUTHORIZATION_TASKS.md), 2026-10-22.
Review context: the project owner considers this proposal low priority and asked for an
assessment of what putting it on hold would leave open.

## Overall assessment

The proposal is architecturally sound: application role + resource authorization +
containment is the right shape, and the open questions (project scope, `do_register`
semantics) are real blockers to implementation, not filler. Low priority is defensible
because the risk surface it targets has already shrunk — but on-hold is only safe if
two ownership gaps it leaves behind are explicitly reassigned. Confidence: High on
repository facts; Medium on deployment reality (whether any deployment still enables
the `sead` ingester).

## Verified current state (basis for the assessment)

- The shared file routes `POST /ingesters/{key}/validate|ingest` still accept a
  caller-supplied `source` path and `output_folder` with no containment check —
  `IngesterService` passes `request.source` straight to the ingester
  (`backend/app/services/ingester_service.py:100,178`). The only gate is
  `application:run_ingesters` (operator role).
- Registered ingesters are `sead` and `sead_change_request`. Change Request file input
  is retired — the shared routes reject it — and the `from-project` routes are
  `project:execute`-gated with no caller paths (route inventory lines 231–247,
  confirmed by the completed handoff and target-bundle work).
- `sead` is deprecated and scheduled for removal under
  [#569](https://github.com/humlab-sead/sead_shape_shifter/issues/569)
  (`ingesters/README.md`, `ingesters/sead/ingester.py:49`).

After #569 ships, the path-based surface this proposal exists to fix is empty: no
registered ingester accepts a caller path through the shared routes.

## Findings

### High — Containment ownership becomes orphaned

`SECURITY_HARDENING_FOLLOWUP.md:44` explicitly declines to own ingester path/destination
containment and defers non-Change-Request operations to this proposal;
`AUTHORIZATION_ROUTE_INVENTORY.md:245` names this proposal as the owner of "source,
destination, and database registration containment checks"; `SECURITY_HARDENING_FOLLOWUP`
`P-AC-2` keeps a stub ("other ingester operations retain their intended permissions")
that only closes if someone owns the checks. On hold, no active document owns them.

*Recommendation:* when moving on hold, either (a) transfer the containment scope for
remaining path-based ingesters into `SECURITY_HARDENING_FOLLOWUP` Phase 4, or (b) record
in both documents that the scope is intentionally deferred pending #569, with
re-evaluation triggered by that removal. Confidence: High.

### Medium — The accepted risk window is the `sead` ingester until #569

While on hold, an operator-role principal can still make the deprecated `sead` ingester
read an arbitrary server path and write directly to the target database. The proposal's
own guardrail — "keep operations unavailable until checks exist" (`P-AC-5`) — is not
currently satisfied for `sead`; today it is available. On hold means accepting that
exposure for the window until #569 lands.

*Recommendation:* before on-hold, confirm #569's removal is on the near-term release
path, or gate `sead`'s file routes as an interim measure. If any deployment enables
`operator` beyond a small trusted team, weight this up. Confidence: High on code, Low
on deployment posture.

### Medium — On-hold reason should name the re-activation trigger

The decision hinges on facts that change: #569 completion, and whether any future
ingester needs file input (the handoff proposal notes future file-only ingesters would
need this design). An on-hold line without a trigger will silently rot.

*Recommendation:* status wording like "On hold; the path-based ingester surface retires
with #569. Re-open if a new file-input ingester is proposed or #569 stalls."
Confidence: High.

### Low — The three Open Questions are genuinely blocking

Project scope, the upload/destination resource model, and `do_register` semantics cannot
be answered from the repo alone. This supports on-hold over "ready but deprioritized."
Confidence: High.

## Consequences summary

| Consequence | Severity | Mitigation |
|---|---|---|
| Containment checks unowned in docs | High | Reassign to SECURITY_HARDENING_FOLLOWUP or record deferral in both docs + route inventory |
| Operator-role arbitrary-path read via `sead` | Medium | Bounded by #569 removal; verify its release timing |
| `P-AC-5` "unavailable" stance unmet meanwhile | Medium | Same window; interim route gate optional |
| Design knowledge rot | Low | On-hold reason with named re-activation trigger |

## Planning readiness

**Decision required.** The proposal itself is sound and its open questions are real, so
on-hold is a legitimate call — but it should not be a silent one. The smallest set of
changes before moving on hold:

1. Resolve the containment-ownership orphan (reassign or record the deferral).
2. State the #569 dependency and re-activation trigger in the Status block.
3. Update the two documents that name this proposal as owner
   (`SECURITY_HARDENING_FOLLOWUP.md`, `AUTHORIZATION_ROUTE_INVENTORY.md`).

This assessment is advice, not approval; the developer retains decision authority.

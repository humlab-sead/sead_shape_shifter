# Production Flip To The Authorized Server

## Status

- Future proposal / not yet approved
- Scope: moving production traffic and users from the old server to the authorization-enabled server
- Goal: move production use to the new server with reviewed per-user access, an exercised fallback, and a recorded security result
- Related: [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md](../CENTRALIZED_AUTHORIZATION_CUTOVER/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PLAN.md), [TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md](../CENTRALIZED_AUTHORIZATION_CUTOVER/TEST_ENVIRONMENT_AUTHORIZATION_CUTOVER_HANDOFF.md), [SECURITY_CHECK.md](../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md)

## Summary

The cutover plan delivers an authorization-enabled deployment on the new server that is ready for user acceptance testing. This proposal covers what follows: accepting that result, provisioning per-user access for the real population, repointing production DNS and the reverse proxy, and holding the old server as the fallback until the move is accepted.

## Problem

The cutover plan explicitly excludes the production move, so without this proposal that work is unowned. Three things make it more than a routing change:

1. **The identity model changes.** The previous setup used a single nginx user that never reached the application. The new deployment authenticates individual principals and evaluates grants per request. Accounts and grants must exist for real users before anyone moves, and an account error becomes an access failure for a real person.
2. **The routing does not exist yet.** No DNS record covers the production web name, and the record that exists still points at the old server. The repoint is the moment users change servers, and its owner is outside this repository.
3. **Acceptance is owned elsewhere.** The trigger for the move is a user acceptance test of the new server, whose criteria are authored and applied by the people who will use the system.

## Scope

**In scope**

- Recording the user acceptance outcome, the criteria used, and the approvers.
- Provisioning per-user accounts and reviewed grants for the production population.
- Selecting and documenting the production Podman service model.
- Repointing production DNS and the reverse proxy to the new server.
- Pre-flip rehearsal, post-flip access and audit verification, and the fallback window.
- Updating the security record for the production deployment.

**Out of scope**

- Rebuilding the deployment or repeating the readiness evidence, which the cutover plan owns.
- Authorization design, policy, and grant changes beyond provisioning reviewed access.
- The focused and full regression evidence for the release, already recorded.

**Non-Goals**

- Decommissioning the old server, which is a separate operational decision taken after the fallback window closes.
- Changing the identity provider or the trustworthy-proxy mechanism.

## Recommended Delivery Order

1. **Acceptance intake.** Record the user acceptance outcome, the criteria exercised, the approvers, and any accepted limitation.
2. **Access provisioning.** Create one account per person whose principal ID matches the value the proxy supplies, grant the reviewed roles, and review the `everyone`/`authenticated` reader grants on the six shared data sources for the real population.
3. **Service model decision.** Select and document the production Podman service model. The recorded deployment currently runs `podman-compose` with a user unit, which `SECURITY_CHECK.md` records as the inspected model; Quadlet remains a candidate if the deployment owner prefers it.
4. **Rehearsal.** Rehearse the repoint and its reverse against a non-production name before the real change.
5. **The flip.** Repoint DNS and the reverse proxy, verify access and audit records, and start the fallback window with a named owner.
6. **Fallback closure and record.** Decide whether to close the window and decommission the old server, then update `SECURITY_CHECK.md` for the production deployment.

## Risks And Tradeoffs

- **Two servers exist during the transition.** Data written on the new server before the flip is test data and must not be mistaken for production records.
- **Rollback reverts the identity model.** Pointing users back to the old server restores the single shared credential, so it is a behavioural downgrade, not only an availability fallback.
- **Per-user accounts are new to this system.** Account provisioning mistakes surface as access failures for real users, so provisioning needs review before the flip, not after.
- **Shared-source reader grants are broad.** Every authenticated principal can read the six shared data sources. That is intended for the current manifest, and it should be confirmed rather than assumed for the production population.
- **The project cannot schedule the flip alone.** The DNS and proxy repoint is owned outside the repository.

## Testing And Validation

- Access checks for a sample of real principals through the production entry point.
- Audit-event review covering the flip window.
- Fallback rehearsal: repoint back and confirm the old server still serves.
- Security record updated with the production deployment's release identity and results.

## Acceptance Criteria

- `P-AC-1` The user acceptance outcome, the criteria exercised, and the approvers are recorded before any user moves.
- `P-AC-2` Every production user has an account whose principal ID matches the identity the proxy supplies, with reviewed grants.
- `P-AC-3` The production DNS and reverse proxy entries resolve to the new server, with the change and its owner recorded.
- `P-AC-4` Post-flip access checks and audit review pass for representative real users.
- `P-AC-5` The fallback to the old server is exercised, and its window, owner, and closure decision are recorded.
- `P-AC-6` `SECURITY_CHECK.md` records the production deployment's tested commit, image digest, results, limitations, and approved exceptions.

## Planning Handoff

- This proposal needs its own phase plan; the criteria above are its source.
- Fixed constraint: no user moves before access provisioning is reviewed, and the old server stays authoritative until the fallback window closes.
- Blocking decisions: the user acceptance owner and criteria, the DNS and proxy owner, the fallback window length, and which deployment user serves production on the new server.

## Open Questions

- Who owns and executes user acceptance testing, and against which criteria?
- Who owns the production DNS and reverse-proxy repoint, and what notice does that change need?
- How long is the fallback window, and who decides to close it?
- Which deployment user serves production on the new server?
- Is data written on the new server before the flip acceptable, or must it be cleared before the move?

## Final Recommendation

Do not schedule the flip until acceptance is recorded and per-user access is provisioned and reviewed. Treat the old server as authoritative until the fallback window closes, and record the identity-model downgrade that a rollback implies.

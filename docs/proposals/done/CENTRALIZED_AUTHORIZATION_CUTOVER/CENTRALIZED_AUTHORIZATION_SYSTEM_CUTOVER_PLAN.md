# Centralized Authorization System Cutover Plan

## Status

- Phase plan / Phases 1, 2, 2A, 3, 4, and 5 complete
- **Phase 5 completion 2026-09-23:** [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md) records the frozen release unit — source commit `dbff5ab9…4f96`, image ID `6a487db7…04a8`, and the locally computed manifest digest — the exposure, container-configuration, grant, proxy-identity, access, route-classification, and rollback results, the limitations, and the approved exceptions. `PH5-AC-1` to `PH5-AC-6` are met and `VM-5.1` to `VM-5.4` are covered. [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md) now carries the tested commit, image identity, results, limitations, and approved exceptions. Two exceptions are recorded, each with its owner: the off-host network probe, accepted by Roger Mähler, and the unread PostgreSQL server log, owned by `super.sead.se`.
- **Phase 4 completion 2026-09-22:** [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md) records the release, manifest, and backup identifiers, the route-inventory, ownership, and audit results, the access checks, and a passing rollback exercise with a byte-identical restore. `PH4-AC-1` to `PH4-AC-5` are met and `VM-4.1` to `VM-4.4` are covered. Phase 5 prerequisites are satisfied by that record. The post-fix re-run of the corrected access-check script was skipped because the principal passwords were not available from the workstation used, and the residual risk is accepted; the record states this under *Post-Fix Re-Run Skipped (Accepted Risk)*, and two cleanups are deferred until after the acceptance window under *Cleanup Deferred Until After Acceptance*.
- Scope: route and operation inventory, migration input, readiness validation, an authorization-enabled deployment ready for user acceptance testing, and Podman release verification
- Goal: deliver and record an authorization-enabled deployment on the new server that is ready for user acceptance testing, together with the operator procedures and documentation needed to run, verify, and roll it back
- **Scope change 2026-09-22:** flipping production traffic and users from the old server to the new server is out of scope. It repoints DNS and the reverse proxy, migrates users, and depends on user acceptance testing this project does not own, so it moves to [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).
- Source decision: [Centralized Authorization System](../../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Related: [Deployment Verification Handoff](./DEPLOYMENT_VERIFICATION_HANDOFF.md), [SECURITY_CHECK.md](../../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md), [Release Cycle Evidence And Locking](../../RELEASE_CYCLE_EVIDENCE_AND_LOCKING/README.md)

## Summary

The authorization repository, policy, route dependencies, service checks, administration CLI, tests, and operating procedures are implemented. What remains is work only a deployment can finish: classify every reachable route and background operation, review the deployment's resources and grants, validate the migration, enable enforcement on a tested release, and record the result.

This plan owns that sequence, the migration input, the rollback decision, and release verification, up to and including a deployment a user acceptance test can be run against. Authorization design stays in the source decision document, deployment check details stay in the handoff, and moving users to the new server is a separate decision.

## Problem

Authorization enforcement denies requests as soon as protected routes are enabled. The new server runs that enforcement from the outset, so it cannot be handed to users for acceptance testing until every sensitive route and background operation has a declared requirement and every deployed resource has reviewed ownership and access grants. It also needs a tested backup, a named rollback decision, and results recorded from the exact release being enabled.

## Scope

This plan covers:

- completing the registered-route and background-operation inventory;
- reviewing project and shared-data-source resource records and locators;
- establishing the target environment configuration layout before manifest application;
- confirming trusted-proxy principal IDs used for administrators and grants;
- preparing, reviewing, applying, and reconciling the initial authorization manifest;
- running focused and full regression validation;
- building and deploying the exact release with Podman;
- recording release, backup, rollback, and post-deployment access results for the new server;
- documenting and exercising the operator procedures for deployment, access management, backup, restore, and rollback;
- assembling the evidence a user acceptance test needs, without authoring or owning its acceptance criteria.

## Non-Goals

- New authorization policy design.
- Native authentication or replacement of the nginx identity provider.
- Ingester capability authorization beyond classifying its current routes and recording follow-up work.
- Authoring or owning user acceptance test criteria, and executing user acceptance testing.
- Repointing production DNS or the reverse proxy from the old server to the new server.
- Migrating production users, accounts, or grants to the new server.
- Selecting the production Podman service model.

## Current Position

- The authorization design, policy, and persistent SQLite repository are implemented.
- Project, child-resource, shared-source, log, session, and operation checks are implemented for the covered routes and services.
- The administration CLI supports manifest migration, reconciliation, resource and role review, grant mutations, backup, restore, and integrity checks.
- Phase 1 is complete: the maintained route inventory classifies every route and lifecycle entry, carries a dated review by Roger Mähler on 2026-09-17, and no longer contains an `UNDECLARED` row. The classification and parity checks in `backend/tests/authorization/test_route_authentication.py` enforce that state.
- The test-target inventory records 26 migration-source projects, 6 shared data sources, confirmed nginx principal IDs and owners/readers, and the reviewed initial manifest. The reviewed project and shared-data content is provisioned on the target, and `sead-options` is verified against the live database. Release and readiness evidence is recorded in the test-environment cutover handoff, and the completed Phase 3 task plan is archived under `done/`.
- The new server `humlabsead.srv.its.umu.se` hosts the authorization-enabled deployment, while the old server continues to run the previous setup. The two never mix: the new server is never provisioned with the pre-authorization deployment, so no partially enforced or mixed-identity period exists there.
- Production DNS still targets the old server, and no record exists yet for the production or staging web names. Repointing them is a separate decision with an owner outside this plan.
- Phase 4 is complete. The deployment record identifies the release, manifest, backup, and rollback owner; the blocking checks, access checks, and audit review are recorded; and the rollback exercise passed with a state-neutral restore. The record also states what is not verified, including that symmetric cross-resource isolation could not be tested, because `bruno` is the only reviewed project owner who is not a global reader.
- The identity model changes with the move. The previous setup used a single nginx user that never reached the application. The new deployment authenticates individual principals and evaluates grants per request, so accounts and grants must exist for real users before any user moves.
- The deployment documentation describes the Podman layout, so the runbook rewrite an earlier draft of this plan expected is largely complete.

## Phase Plan

### Phase 1: Complete Route And Operation Inventory

**Goal**

Classify every registered route and background operation that production can reach.

**Focus**

- Reconcile the maintained route inventory with all registered FastAPI routes, static mounts, and direct application routes.
- Classify the remaining `UNDECLARED` routes as public, authenticated-only, or protected by an explicit application or resource requirement.
- Identify background operations, lifecycle entry points, and sensitive service methods that require an authorized resource.
- Confirm project and shared-data-source create, copy, delete, and rename paths use the resource lifecycle service.

**Depends On**

- No prior phase.

**Outputs**

- A classified route and operation inventory for Phases 2–5.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-1`) No sensitive production route or background operation remains `UNDECLARED`.
- `PH1-AC-2` (from `P-AC-1`) The inventory records the resource type, action, and exposure status for every registered route.
- `PH1-AC-3` (from `P-AC-1`) Lifecycle entry points and protected service methods have a reviewed authorization owner and requirement.
- `PH1-AC-4` (from `P-AC-4`) The automated route inventory check passes.

**Validation Milestones**

- `VM-1.1` The route inventory check reports no undeclared non-health route (covers `PH1-AC-1`, `PH1-AC-4`).
- `VM-1.2` Review of the inventory against the registered routes confirms classification and owner for every entry (covers `PH1-AC-2`, `PH1-AC-3`).

**Task-Plan Handoff**

- Source criteria: `PH1-AC-1` to `PH1-AC-4`; fixed constraint: the inventory must be compared with the registered route set, not a hand-maintained list.
- The task plan must name the inventory check, the classification categories, and the reviewer. Stop if a route cannot be classified without a policy decision.

**Readiness**

Complete on 2026-09-17; executed through the [Phase 1 task plan](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_1_TASK_PLAN.md).

### Phase 2: Review Deployment Resources And Initial Grants

**Goal**

Produce the deployment's authorization inputs without modifying project YAML.

**Focus**

- Inventory every deployed project and shared data source, including its current locator and expected lifecycle state.
- Check that no active project or shared-data-source locator is duplicated or conflicts with a resource record.
- Confirm that administrator, owner, and reader principal IDs match the case-sensitive identities supplied by nginx.
- Prepare and review the initial administrator and resource-grant manifest.

**Depends On**

- The Phase 1 inventory, so newly classified routes are covered by the manifest review.

**Outputs**

- A reviewed initial manifest, a resource list, and confirmed principal IDs for Phases 3–5.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) The reviewed manifest includes every required administrator, project, shared data source, and initial grant.
- `PH2-AC-2` (from `P-AC-2`) Required resources have one or more reviewed owners or readers before migration.
- `PH2-AC-3` (from `P-AC-3`) Principal IDs are confirmed against deployment identity values, with corrections recorded before application.
- `PH2-AC-4` (from `P-AC-2`) Project YAML and other user-editable project data are unchanged by the migration-input process.

**Validation Milestones**

- `VM-2.1` Review of the prepared manifest lists every administrator, resource, and grant with no unresolved identity (covers `PH2-AC-1`, `PH2-AC-3`).
- `VM-2.2` Review confirms every required resource has an owner or reader and that project YAML is unchanged (covers `PH2-AC-2`, `PH2-AC-4`).

**Task-Plan Handoff**

- Source criteria: `PH2-AC-1` to `PH2-AC-4`; fixed constraint: do not infer principal ownership from filenames, project metadata, or request data.
- The task plan must name the deployment identity source, the resource owners, and the manifest review step. Stop if identity values or owner names are unavailable.

**Readiness**

Complete for the test target on 2026-09-22; the reviewed manifest was applied and reconciled with zero missing records. Provisioning the reviewed project and shared-data content, or regenerating the policy for the target content, remains a follow-up before treating the target dataset as ready for users.

### Phase 2A: Establish Target Environment Configuration Layout

**Goal**

Move deployment-specific configuration and authorization inputs to the external `config` directory while keeping mutable runtime data in `container-data` and deployment code in the replaceable `container` checkout.

**Focus**

- Establish the `container` / `config` / `container-data` path contract for Make, Compose, lifecycle scripts, systemd, and deployment helpers.
- Provision target configuration and authorization inputs without repository-local secrets or runtime files under `container`.
- Preserve the interim UCanAccess build dependency under `container/lib/ucanaccess`.
- Verify that configuration and data survive replacement of the `container` checkout.

**Depends On**

- Phase 1 route and operation inventory.
- Phase 2 manifest review may be completed before this phase; the reviewed manifest is provisioned into the target `config` directory as part of this phase.

**Outputs**

- A validated target configuration contract and three-directory deployment layout.
- Target-provisioned deployment, runtime, authorization, and credential files owned by the deployment user.
- A replacement-tested `container` checkout with preserved `config` and `container-data`.

**Acceptance Criteria**

- `PH2A-AC-1` (supplemental prerequisite; task-plan `CFG-AC-1` through `CFG-AC-3`) Make, Compose, lifecycle scripts, systemd, and deployment helpers resolve the target `config` and `container-data` paths without requiring live configuration under `container`.
- `PH2A-AC-2` (supplemental prerequisite; task-plan `CFG-AC-4` and `CFG-AC-5`) Authorization credentials, groups, and manifest are read from target `config`; the deployment user owns all of `~/config`; setup preserves existing files and applies restrictive credential permissions.
- `PH2A-AC-3` (supplemental prerequisite; task-plan `CFG-AC-6` and `CFG-AC-7`) The replacement-tested image build preserves UCanAccess support from `container/lib/ucanaccess`, while runtime configuration, authorization state, credentials, and backups remain in their designated locations.
- `PH2A-AC-4` (supplemental prerequisite; task-plan `CFG-AC-8`) Deployment documentation and verification commands describe the three-directory layout and do not present retired paths as current practice.

**Validation Milestones**

- `VM-2A.1` Temporary Make, loader, Compose, and systemd checks resolve identical absolute configuration and data paths (covers `PH2A-AC-1`).
- `VM-2A.2` Fresh setup, idempotence, authorization bootstrap, and permission checks pass with a temporary target `config` directory (covers `PH2A-AC-2`).
- `VM-2A.3` Local and configured GitHub/ref builds succeed with UCanAccess under `container/lib/ucanaccess`, and replacement preserves `config` and `container-data` (covers `PH2A-AC-3`).
- `VM-2A.4` Documentation and stale-path review pass (covers `PH2A-AC-4`).

**Task-Plan Handoff**

- Execute [Target Environment Configuration Layout Task Plan](./done/TARGET_ENVIRONMENT_CONFIGURATION_LAYOUT_TASK_PLAN.md). **Complete:** the test target uses the three-directory layout and the task plan's Definition of Done is satisfied.
- Fixed decisions: the deployment user owns all of `~/config`; UCanAccess remains under `container/lib/ucanaccess` as an interim build-dependency exception; no fallback to `container/.env`, `secrets/.env`, or `container-data/backend.env` is required.
- Phase 2A is a prerequisite for Phase 3 manifest application and reconciliation, but it is not a prerequisite for completing the Phase 2 manifest review.

**Readiness**

Complete for the test target on 2026-09-22; the linked task plan's Definition of Done is satisfied. Phase 3 is no longer blocked by the configuration layout. The remaining Phase 3 prerequisite is a release candidate and its focused/full regression evidence.

### Phase 3: Validate Migration And Cutover Readiness

**Goal**

Prove that the reviewed authorization state and the release candidate are ready for enforcement.

**Focus**

- Run focused authorization tests and the full backend regression suite.
- Inspect the manifest with dry-run mode, apply it, and run reconciliation.
- Verify that reconciliation reports no missing administrators, resources, or grants.
- Create an integrity-checked authorization database backup and copy it to operator-controlled storage.
- Run allowed and denied access checks for an administrator, a project owner, and a principal without grants.

**Depends On**

- The Phase 2 reviewed manifest and confirmed principal IDs.
- Phase 2A target configuration layout and authorization input provisioning.
- A release candidate built from the intended commit.

**Outputs**

- Validated migration input, a stored and integrity-checked backup, and access-check results for Phases 4–5.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) Focused authorization tests and the full backend regression suite pass.
- `PH3-AC-2` (from `P-AC-5`) The applied manifest reconciles with zero missing records.
- `PH3-AC-3` (from `P-AC-5`) No required resource is unowned and no active locator conflict remains.
- `PH3-AC-4` (from `P-AC-2`) Existing projects and shared resources have reviewed initial grants before enforcement.
- `PH3-AC-5` (from `P-AC-6`) The backup passes integrity checking and its storage location is recorded.
- `PH3-AC-6` (from `P-AC-7`) Access checks confirm permitted and denied outcomes for the required principal classes.

**Validation Milestones**

- `VM-3.1` Focused authorization tests and the full backend regression suite pass on the release candidate (covers `PH3-AC-1`).
- `VM-3.2` Dry-run inspection, application, and reconciliation report zero missing records and no unowned resource (covers `PH3-AC-2` to `PH3-AC-4`).
- `VM-3.3` The backup passes integrity checking and the stored copy is recorded on operator-controlled storage (covers `PH3-AC-5`).
- `VM-3.4` Access checks return the expected permitted and denied results for administrator, project owner, and unprivileged principals (covers `PH3-AC-6`).

**Task-Plan Handoff**

- Source criteria: `PH3-AC-1` to `PH3-AC-6`; fixed constraint: the backup and access-check results must come from the release candidate, not an earlier build.
- The task plan must name the test commands, the dry-run and reconciliation steps, the backup destination, and the access-check principals.

**Readiness**

Ready for a Phase 3 task plan. Phase 2's reviewed manifest and confirmed principals are complete, and Phase 2A's target configuration migration is complete. Phase 3 must still record its own release-candidate regression, backup, migration, reconciliation, and access-check evidence before it can be marked complete.

### Phase 4: Deliver And Record The UAT-Ready Deployment

**Goal**

Deliver an authorization-enabled deployment on the new server that a user acceptance test can be run against, and record it with its operator procedures exercised.

**Focus**

- Record the release commit, manifest revision, authorization database backup, and rollback decision owner.
- Confirm the new server runs the recorded release with enforcement active for the classified routes.
- Repeat access checks and inspect authorization audit records against that deployment.
- Exercise the documented backup, restore, and rollback procedures against the deployment, and record what a rollback discards.
- Assemble the evidence a user acceptance test needs, and record the deployment result, exceptions, and limitations.

**Depends On**

- Phases 1–3 complete, including the stored backup and access-check results.
- A release build on the new server whose commit and image digest are recorded.
- A named rollback decision owner.

**Outputs**

- A deployment record with the release identity, the results, the exercised procedures, and the evidence pack for user acceptance testing.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-7`) The deployment record identifies the release, manifest, backup, and rollback decision owner.
- `PH4-AC-2` (from `P-AC-7`) Post-deployment checks confirm expected administrator, owner, and denied-principal behavior.
- `PH4-AC-3` (from `P-AC-7`) Authorization audit records exist for the migration and later administrative mutations.
- `PH4-AC-4` (from `P-AC-8`) A rollback restores a valid authorization database, and reconciliation completes afterward.
- `PH4-AC-5` (from `P-AC-1`, `P-AC-2`) An unclassified route, unowned resource, identity mismatch, or failed check blocks the deployment from being presented for acceptance instead of being accepted without review.

**Validation Milestones**

- `VM-4.1` The recorded release, manifest, and backup identifiers match the running deployment (covers `PH4-AC-1`).
- `VM-4.2` Post-deployment access checks and audit review return the expected results (covers `PH4-AC-2`, `PH4-AC-3`).
- `VM-4.3` The rollback exercise restores a valid database and reconciliation completes (covers `PH4-AC-4`).
- `VM-4.4` The blocking check shows no unresolved route, resource, identity, or validation failure (covers `PH4-AC-5`).

**Task-Plan Handoff**

- Source criteria: `PH4-AC-1` to `PH4-AC-5`; fixed constraint: the rollback backup records the state at backup time, so grants added afterwards are lost on rollback.
- The task plan must name the export and inspection commands, the audit inspection, the blocking-check records, the exercised procedures, and the evidence pack handed to the user acceptance test owners.
- Moving users to the new server is not part of this phase.

**Readiness**

Complete on 2026-09-22. The task plan is [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_4_TASK_PLAN.md) and the resulting record is [UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md](./done/UAT_READY_AUTHORIZATION_DEPLOYMENT_HANDOFF.md).

### Phase 5: Verify Podman Deployment And Update Security Record

**Goal**

Verify the authorization release in the Podman deployment and record security results for that release.

**Focus**

- Confirm release identity: an immutable image identified by its source commit and image digest, never a mutable `latest` tag.
- Confirm exposure: the backend is published on loopback only, the reverse proxy is the only external entry point, client identity headers are removed and replaced, and firewall rules plus Podman network settings restrict direct access.
- Confirm secrets and mounts: Podman-compatible secret injection, reviewed mounts, no credentials in the image, logs, client-controlled settings, or unintended container paths, and no sensitive host files exposed to the container.
- Confirm deployment behavior: health checks, restart behavior, the single-worker requirement, logs, PostgreSQL role grants, authorization database location, and project and shared-data mounts.
- Confirm the deployment runbook and operator artifacts describe the deployed layout, commands, paths, service lifecycle, health checks, logs, and rollback.
- Run post-deployment allowed and denied access checks, review container, proxy, and database logs, and exercise rollback with the recorded image, service definition, database backup, and integrity and reconciliation checks.
- Update `SECURITY_CHECK.md` with the tested commit, image digest, results, limitations, and approved exceptions.

**Depends On**

- Phases 1–4 complete, including the reviewed manifest, the stored backup, and the deployment record.
- The new server deployment from Phase 4, including its release identity and rollback result.
- The deployment check results tracked in [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md).

**Outputs**

- A Podman deployment record containing the source commit, image digest, service definition revision, mounts, secrets, network exposure, grants, logs, smoke checks, and rollback result.
- An updated `SECURITY_CHECK.md` and a release disposition for every finding.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-9`) The recorded source commit and image digest match the running Podman container.
- `PH5-AC-2` (from `P-AC-9`) The backend port is published on loopback only, and proxy and firewall checks show no untrusted direct access.
- `PH5-AC-3` (from `P-AC-9`) Proxy identity-header handling, health behavior, allowed access, denied access, and cross-resource isolation pass after deployment.
- `PH5-AC-4` (from `P-AC-9`) Secrets, mounts, environment variables, PostgreSQL grants, authorization database placement, and logs meet the approved security rules without credential disclosure.
- `PH5-AC-5` (from `P-AC-8`) Backup integrity, restore and reconciliation, and application rollback checks pass, or a reviewed exception records the failed check and release disposition.
- `PH5-AC-6` (from `P-AC-10`) `SECURITY_CHECK.md` records the tested commit, image digest, results, limitations, and approved exceptions for each finding.

**Validation Milestones**

- `VM-5.1` Image, service, port, proxy, firewall, secret, mount, and environment inspection passes (covers `PH5-AC-1`, `PH5-AC-2`, `PH5-AC-4`).
- `VM-5.2` Post-deployment authorization and security smoke checks pass for administrator, project owner, and denied principal (covers `PH5-AC-3`).
- `VM-5.3` Backup, restore, and rollback checks pass with integrity and manifest reconciliation (covers `PH5-AC-5`).
- `VM-5.4` The security record and the disposition for every finding are updated and reviewed (covers `PH5-AC-6`).

**Task-Plan Handoff**

- Source criteria: `PH5-AC-1` to `PH5-AC-6`; fixed constraint: a result recorded for one image digest carries no weight for another.
- The task plan must define the exact host and container paths, secret mechanism, proxy and firewall inspection method, database-grant queries, image identity commands, and rollback procedure.
- Stop before deployment if the host, proxy configuration, firewall access, or database administrator results are unavailable.

**Readiness**

Complete on 2026-09-23. The task plan is [CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_5_TASK_PLAN.md](./done/CENTRALIZED_AUTHORIZATION_SYSTEM_CUTOVER_PHASE_5_TASK_PLAN.md), trimmed to the checks the frozen release unit invalidates, and the resulting record is [PODMAN_DEPLOYMENT_RECORD.md](./PODMAN_DEPLOYMENT_RECORD.md). The deployment host is the new server. The production Podman service model is deferred to [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md), and these checks apply to the deployment as installed.

## Cross-Phase Rules

- Do not enable enforcement while a sensitive route or background operation remains unclassified.
- Do not modify project YAML to assign authorization ownership or grants.
- Treat the reviewed manifest and the generation-specific resource records as the source of migration input.
- Keep the backup created for readiness testing available until user acceptance testing concludes or the fallback to the old server is no longer available.
- Do not repoint production DNS or the reverse proxy from the old server to the new server under this plan; the flip is owned by [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).
- Do not provision the new server with the pre-authorization deployment, so the two identity models never coexist there.
- Keep the current authorization policy unchanged during deployment unless a separate approved design change is made.

## Validation Strategy

- Compare the route inventory with registered FastAPI routes and the production deployment shape.
- Run the automated inventory check, the focused authorization tests, and the full backend regression suite before release approval.
- Inspect and apply the manifest with dry-run and reconciliation checks.
- Run database integrity checks before and after backup, restore, and deployment.
- Run allowed and denied access checks with known deployment principals before and after deploying the recorded release to the new server.
- For the Podman deployment, inspect the image digest, service definition, published ports, network and firewall exposure, proxy identity handling, secrets, mounts, environment variables, grants, logs, health checks, rollback, and exception records.

Exact test and inspection commands belong in the phase task plans.

## Acceptance Criteria

- `P-AC-1` No sensitive route or background operation reachable in production remains `UNDECLARED`.
- `P-AC-2` Deployment resource records, administrators, owners or readers, and initial grants are reviewed and recorded outside project YAML.
- `P-AC-3` Principal IDs match the identities supplied by nginx, with corrections recorded before manifest application.
- `P-AC-4` The automated route inventory check, the focused authorization tests, and the full backend regression suite pass on the release commit.
- `P-AC-5` The reviewed manifest applies and reconciles with no missing administrator, resource, or grant.
- `P-AC-6` An integrity-checked authorization database backup is stored on operator-controlled storage with its location recorded.
- `P-AC-7` Enforcement runs on the tested release, and post-deployment checks confirm administrator, project owner, and denied-principal outcomes.
- `P-AC-8` A rollback restores a valid authorization database, and reconciliation completes afterward.
- `P-AC-9` The Podman deployment record identifies the running container's source commit and image digest and covers exposure, secrets, mounts, grants, logs, and service behavior.
- `P-AC-10` `SECURITY_CHECK.md` records the tested commit, image digest, results, limitations, and approved exceptions for every finding.

## Open Questions

These decisions block phases, and [DEPLOYMENT_VERIFICATION_HANDOFF.md](./DEPLOYMENT_VERIFICATION_HANDOFF.md) tracks their current state.

- Which deployment user serves the production instance once users move to the new server? Resolve in [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).
- Who owns and executes user acceptance testing, and against which criteria? Resolve before any user moves to the new server.
- Who owns the production flip, the DNS and proxy repoint, and user migration? Resolve in [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).
- Does the deployment keep the shared `sead_ro` account or use an application-specific read-only account? The database administrator owns this decision; resolve before Phase 5.

## Final Recommendation

Treat this plan as the gate for a deployment ready for user acceptance testing, not for moving users. Complete the phases in order, and do not present a deployment for acceptance until every acceptance criterion passes or an explicitly reviewed exception is recorded. The rollback decision owner is Roger Mähler. Moving production users to the new server is a separate decision, covered by [PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md](../../future/PRODUCTION_FLIP_TO_AUTHORIZED_SERVER.md).

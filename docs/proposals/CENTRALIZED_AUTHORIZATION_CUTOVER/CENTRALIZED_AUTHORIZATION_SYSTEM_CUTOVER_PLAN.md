# Centralized Authorization System Cutover Plan

## Status

- Phase plan / not yet executed
- Scope: route and operation inventory, migration input, readiness validation, enforcement cutover, and Podman release verification
- Goal: enforce the implemented authorization system in production with reviewed access records and a tested rollback
- Source decision: [Centralized Authorization System](../done/MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM.md)
- Related: [Deployment Verification Handoff](./DEPLOYMENT_VERIFICATION_HANDOFF.md), [SECURITY_CHECK.md](../done/MITIGATE_SECURITY_ISSUES/SECURITY_CHECK.md)

## Summary

The authorization repository, policy, route dependencies, service checks, administration CLI, tests, and operating procedures are implemented. What remains is work only a deployment can finish: classify every reachable route and background operation, review the deployment's resources and grants, validate the migration, enable enforcement on a tested release, and record the result.

This plan owns that sequence, the migration input, the rollback decision, and release verification. Authorization design stays in the source decision document, and deployment check details stay in the handoff.

## Problem

Authorization enforcement denies requests as soon as protected routes are enabled. Cutover is unsafe until every sensitive route and background operation has a declared requirement and every deployed resource has reviewed ownership and access grants. Cutover also needs a tested backup, a named rollback decision, and results recorded from the exact release being enabled.

## Scope

This plan covers:

- completing the registered-route and background-operation inventory;
- reviewing project and shared-data-source resource records and locators;
- confirming trusted-proxy principal IDs used for administrators and grants;
- preparing, reviewing, applying, and reconciling the initial authorization manifest;
- running focused and full regression validation;
- building and deploying the exact release with Podman;
- recording release, backup, rollback, and post-deployment access results.

## Non-Goals

- New authorization policy design.
- Native authentication or replacement of the nginx identity provider.
- Ingester capability authorization beyond classifying its current routes and recording follow-up work.

## Current Position

- The authorization design, policy, and persistent SQLite repository are implemented.
- Project, child-resource, shared-source, log, session, and operation checks are implemented for the covered routes and services.
- The administration CLI supports manifest migration, reconciliation, resource and role review, grant mutations, backup, restore, and integrity checks.
- The maintained route inventory still contains `UNDECLARED` entries that require classification before cutover.
- Deployment-specific projects, shared data sources, principal IDs, initial grants, and release evidence are not recorded yet.
- The deployment documentation still describes Docker Compose; the target server uses Podman, so the image, service definition, secret injection, volume mounts, health checks, logging, and rollback workflow need a Podman deployment record.

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

Ready for a task plan.

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

Requires named deployment identities and resource owners.

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

Ready for a task plan once the Phase 2 manifest is reviewed.

### Phase 4: Execute And Record Enforcement Cutover

**Goal**

Enable the tested release and preserve a repeatable rollback path.

**Focus**

- Record the release commit, manifest revision, authorization database backup, and rollback decision owner.
- Deploy the release with authorization enforcement enabled for the classified routes.
- Repeat post-deployment access checks and inspect authorization audit records.
- If cutover fails, stop the service, restore the recorded backup with the documented procedure, restart, run integrity checks, and reconcile the manifest.
- Record the cutover result, exceptions, any rollback result, and follow-up work.

**Depends On**

- Phases 1–3 complete, including the stored backup and access-check results.
- A release build whose commit and image digest are recorded.
- A named rollback decision owner.

**Outputs**

- A cutover record with the enabled release, the results, and the rollback outcome for Phase 5.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-7`) The deployment record identifies the release, manifest, backup, and rollback decision owner.
- `PH4-AC-2` (from `P-AC-7`) Post-deployment checks confirm expected administrator, owner, and denied-principal behavior.
- `PH4-AC-3` (from `P-AC-7`) Authorization audit records exist for the migration and later administrative mutations.
- `PH4-AC-4` (from `P-AC-8`) A rollback restores a valid authorization database, and reconciliation completes afterward.
- `PH4-AC-5` (from `P-AC-1`, `P-AC-2`) An unclassified route, unowned resource, identity mismatch, or failed check blocks cutover instead of being accepted without review.

**Validation Milestones**

- `VM-4.1` The recorded release, manifest, and backup identifiers match the running deployment (covers `PH4-AC-1`).
- `VM-4.2` Post-deployment access checks and audit review return the expected results (covers `PH4-AC-2`, `PH4-AC-3`).
- `VM-4.3` The rollback exercise restores a valid database and reconciliation completes (covers `PH4-AC-4`).
- `VM-4.4` The blocking check shows no unresolved route, resource, identity, or validation failure (covers `PH4-AC-5`).

**Task-Plan Handoff**

- Source criteria: `PH4-AC-1` to `PH4-AC-5`; fixed constraint: the rollback backup records the state at backup time, so grants added afterwards are lost on rollback.
- The task plan must name the rollback procedure and its owner, the audit inspection, and the blocking-check records.

**Readiness**

Requires a named rollback decision owner.

### Phase 5: Verify Podman Deployment And Update Security Record

**Goal**

Verify the authorization release in the Podman deployment and record security results for that release.

**Focus**

- Select and document the Podman service model for the server, with systemd Quadlet as the recommended production option unless the deployment owner approves another supported model.
- Confirm release identity: an immutable image identified by its source commit and image digest, never a mutable `latest` tag.
- Confirm exposure: the backend is published on loopback only, the reverse proxy is the only external entry point, client identity headers are removed and replaced, and firewall rules plus Podman network settings restrict direct access.
- Confirm secrets and mounts: Podman-compatible secret injection, reviewed mounts, no credentials in the image, logs, client-controlled settings, or unintended container paths, and no sensitive host files exposed to the container.
- Confirm deployment behavior: health checks, restart behavior, the single-worker requirement, logs, PostgreSQL role grants, authorization database location, and project and shared-data mounts.
- Rewrite the deployment runbook and operator artifacts for Podman, covering workflow, commands, paths, service lifecycle, health checks, logs, and rollback.
- Run post-deployment allowed and denied access checks, review container, proxy, and database logs, and exercise rollback with the recorded image, service definition, database backup, and integrity and reconciliation checks.
- Update `SECURITY_CHECK.md` with the tested commit, image digest, results, limitations, and approved exceptions.

**Depends On**

- Phases 1–4 complete, including the reviewed manifest, the stored backup, and the cutover record.
- A selected deployment host and an approved Podman service model.
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
- The task plan must define the selected Podman service model, exact host and container paths, secret mechanism, proxy and firewall inspection method, database-grant queries, image identity commands, and rollback procedure.
- Stop before deployment if the host, service model, proxy configuration, firewall access, or database administrator results are unavailable.

**Readiness**

Requires a named deployment host, an approved Podman service model, and access to the reverse proxy, firewall, container runtime, and PostgreSQL grant information.

## Cross-Phase Rules

- Do not enable enforcement while a sensitive route or background operation remains unclassified.
- Do not modify project YAML to assign authorization ownership or grants.
- Treat the reviewed manifest and the generation-specific resource records as the source of migration input.
- Keep the backup created for readiness testing available until the deployment is accepted or the rollback window closes.
- Record unresolved deployment facts as explicit blockers; do not infer principal ownership from filenames, project metadata, or request data.
- Keep the current authorization policy unchanged during cutover unless a separate approved design change is made.

## Validation Strategy

- Compare the route inventory with registered FastAPI routes and the production deployment shape.
- Run the automated inventory check, the focused authorization tests, and the full backend regression suite before release approval.
- Inspect and apply the manifest with dry-run and reconciliation checks.
- Run database integrity checks before and after backup, restore, and cutover.
- Run allowed and denied access checks with known deployment principals before and after cutover.
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

- Which host and environment carry the release deployment? Resolve before Phase 5.
- Who owns the rollback decision, and how long does the pre-cutover backup stay available? Resolve before Phase 4.
- Who approves an exception when a check cannot be performed? Resolve before Phase 4.
- Does the deployment keep the shared `sead_ro` account or use an application-specific read-only account? The database administrator owns this decision; resolve before Phase 5.

## Final Recommendation

Treat this plan as the gate for authorization enforcement cutover. Complete the phases in order, and block production enforcement until every acceptance criterion passes or an explicitly reviewed exception is recorded.

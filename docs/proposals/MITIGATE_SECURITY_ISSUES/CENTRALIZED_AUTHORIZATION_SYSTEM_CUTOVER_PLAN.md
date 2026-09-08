# Centralized Authorization System Cutover Plan

## Summary

This plan sequences the remaining work required to move the implemented centralized authorization system into enforced production use. The authorization repository, policy, route dependencies, service checks, administration CLI, tests, and operating procedures are implemented. Deployment inventory, final route classification, release readiness, and cutover evidence remain.

The plan is separate from the authorization design and implementation task plan. It owns the remaining inventory, migration-input, validation, cutover, and rollback tasks.

## Problem

Authorization enforcement can deny requests as soon as protected routes are enabled, but cutover is unsafe until every sensitive route and background operation has a declared requirement and every deployed resource has reviewed ownership and access grants. The deployment also needs a tested backup, a known rollback decision, and evidence from the exact release being enabled.

## Scope

This plan covers:

- completing the registered-route and background-operation inventory;
- reviewing project and shared-data-source resource records and locators;
- confirming trusted-proxy principal IDs used for administrators and grants;
- preparing, reviewing, applying, and reconciling the initial authorization manifest;
- running focused and full regression validation;
- recording release, backup, rollback, and post-deployment access evidence.

It does not cover new authorization policy design, native authentication, or ingester capability authorization beyond classifying its current routes and recording any required follow-up.

## Current Position

- The authorization design and persistent SQLite repository are implemented.
- Project, child-resource, shared-source, log, session, and operation checks are implemented for the covered routes and services.
- The administration CLI supports manifest migration, reconciliation, resource and role review, grant mutations, backups, restore, and integrity checks.
- The maintained route inventory still contains `UNDECLARED` entries that require classification before cutover.
- Deployment-specific projects, shared data sources, principal IDs, initial grants, release evidence, and rollback evidence have not been recorded as complete.

## Phase Plan

### Phase 1: Complete Route And Operation Inventory

**Goal**

Classify every registered route and background operation that can be reached in the production deployment.

**Focus**

- Reconcile the maintained route inventory with all registered FastAPI routes, static mounts, and direct application routes.
- Classify the remaining `UNDECLARED` routes as public, authenticated-only, or protected by an explicit application/resource requirement.
- Identify background operations, lifecycle entry points, and sensitive service methods that require an authorized resource.
- Confirm project and shared-data-source create, copy, delete, and any rename paths use the resource lifecycle service.

**Acceptance Criteria**

- No sensitive production route or background operation remains `UNDECLARED`.
- The route inventory records the resource type, action, and exposure status for every registered route.
- Lifecycle entry points and protected service methods have a reviewed authorization owner and requirement.
- The automated route inventory check passes.

### Phase 2: Review Deployment Resources And Initial Grants

**Goal**

Produce the deployment-specific authorization inputs without modifying project YAML.

**Focus**

- Inventory every deployed project and shared data source, including its current locator and expected lifecycle state.
- Check that no active project or shared-data-source locator is duplicated or conflicts with a resource record.
- Confirm administrator, owner, and reader principal IDs exactly match the case-sensitive identities supplied by nginx.
- Prepare and review the initial administrator and resource-grant manifest.

**Acceptance Criteria**

- The reviewed manifest includes every required administrator, project, shared data source, and initial grant.
- Required resources have one or more reviewed owners or readers before migration.
- Principal IDs are confirmed against deployment identity values, with corrections recorded before application.
- Project YAML and other user-editable project data are unchanged by the migration-input process.

### Phase 3: Validate Migration And Cutover Readiness

**Goal**

Prove that the exact authorization state and release are ready for enforcement.

**Focus**

- Run focused authorization tests and the full backend regression suite.
- Inspect the manifest with dry-run mode, apply it, and run reconciliation.
- Verify that reconciliation reports no missing administrators, resources, or grants.
- Create an integrity-checked authorization database backup and copy it to operator-controlled storage.
- Run allowed and denied access checks for an administrator, a project owner, and a principal without grants.

**Acceptance Criteria**

- Focused authorization tests and the full backend regression suite pass.
- The applied manifest reconciles with zero missing records.
- No required resource is unowned and no active locator conflict remains.
- Existing projects and shared resources have reviewed initial grants before enforcement cutover.
- The backup passes integrity checking and its storage location is recorded.
- Access checks confirm both permitted and denied outcomes for the required principal classes.

### Phase 4: Execute And Record Enforcement Cutover

**Goal**

Enable the tested release and preserve a repeatable rollback path.

**Focus**

- Record the exact release commit, manifest revision, authorization database backup, and rollback decision owner.
- Deploy the release with authorization enforcement enabled for the classified routes.
- Repeat post-deployment access checks and inspect authorization logs/audit events.
- If cutover fails, stop the service, restore the recorded backup using the documented procedure, restart, run integrity checks, and reconcile the manifest.
- Record the cutover result, exceptions, rollback result if used, and follow-up work.

**Acceptance Criteria**

- The deployment record identifies the exact release, manifest, backup, and rollback decision owner.
- Post-deployment checks confirm expected administrator, owner, and denied-principal behavior.
- Authorization audit events are present for migration and subsequent administrative mutations.
- A rollback can restore a valid authorization database and reconciliation completes afterward.
- Any unclassified route, unowned resource, identity mismatch, or failed check blocks cutover rather than being accepted as an exception without review.

## Cross-Phase Rules

- Do not enable enforcement while a sensitive route or background operation remains unclassified.
- Do not modify project YAML to assign authorization ownership or grants.
- Treat the reviewed manifest and the generation-specific resource records as the source of migration input.
- Keep the backup created for readiness testing available until the deployment is accepted or the rollback window closes.
- Record unresolved deployment facts as explicit blockers; do not infer principal ownership from filenames, project metadata, or request data.
- Keep the current authorization policy unchanged during cutover unless a separate approved design change is made.

## Validation Strategy

- Review the route inventory against registered FastAPI routes and the production deployment shape.
- Run the automated route inventory check and focused authorization tests.
- Run the full backend regression suite before release approval.
- Inspect and apply the manifest with dry-run and reconciliation checks.
- Run database integrity checks before and after backup, restore, and cutover.
- Perform post-deployment allowed and denied access checks using known deployment principals.
- Review the deployment record for release, manifest, backup, rollback, and exception evidence.

## Final Recommendation

Treat this plan as the gate for authorization enforcement cutover. Complete the phases in order, and block production enforcement until all acceptance criteria pass or an explicitly reviewed exception is recorded.

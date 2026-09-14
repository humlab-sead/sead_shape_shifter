# Task Plan: Ingester Authorization

## Phase Summary

- Status: Not started
- Related authorization plan: [CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md](../MITIGATE_SECURITY_ISSUES/done/CENTRALIZED_AUTHORIZATION_SYSTEM_TASK_PLAN.md)
- Related security-hardening phase 4 work now tracked here: [MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md](../MITIGATE_SECURITY_ISSUES/MITIGATE_SECURITY_ISSUES_PHASE_4_TASK_PLAN.md)
- Goal: define and implement authorization for the ongoing `sead_change_request` ingester without enabling operations that still lack required containment and destination checks.

**Acceptance Criteria**

- [ ] Nonsensitive ingester metadata requires an authenticated principal.
- [ ] Ingester validation and execution require the `operator` application role.
- [ ] Ingester configuration and registration require the `admin` application role.
- [ ] The ingester API disposition is documented here instead of in the security-hardening phase 4 plan.
- [ ] Unsafe ingester operations remain unavailable until project, source, database, destination, and containment authorization checks exist.
- [ ] Every approved ingester operation authorizes its source and destination.
- [ ] Cross-user, cross-project, cross-source, and ingester authorization tests pass.

## Work Breakdown

### 1. Classify Ingester Routes And Operations

**Objective**

Identify each ingester route and background operation, its sensitivity, and its required application or resource authorization.

**Tasks**

- [ ] Classify nonsensitive ingester metadata endpoints that require authenticated access.
- [ ] Identify validation and execution entry points that require the `operator` role.
- [ ] Identify configuration and registration entry points that require the `admin` role.
- [ ] Record source, project, database, and destination inputs for each ingester operation.

**Completion Criteria**

Every ingester entry point has a documented authorization requirement and identified source and destination inputs.

### 2. Enforce Application Roles

**Objective**

Apply the central authorization policy to ingester routes and operations.

**Tasks**

- [ ] Require an authenticated principal for nonsensitive ingester metadata.
- [ ] Require `operator` authorization for ingester validation and execution.
- [ ] Require `admin` authorization for ingester configuration and registration.
- [ ] Ensure service and background-operation entry points cannot bypass the declared route authorization.

**Completion Criteria**

Ingester metadata, validation, execution, configuration, and registration reject principals without the required application role.

### 3. Protect Approved Operations

**Objective**

Authorize every source and destination before enabling an ingester operation.

**Tasks**

- [ ] Define authorization and containment checks for each source, project, database, and destination used by an approved operation.
- [ ] Keep operations disabled when any required authorization or containment check is unavailable.
- [ ] Pass authorized resources to the operation implementation before it reads or writes protected data.
- [ ] Document whether the ingester API remains disabled, is removed, or is redesigned around uploaded content and server-managed destinations.

**Completion Criteria**

No approved ingester operation can access an unauthorized source or destination, and unsupported operations remain disabled.

### 4. Validate Authorization Behavior

**Objective**

Prove ingester authorization rules across principals and resources.

**Tasks**

- [ ] Add unauthenticated, unauthorized, and allowed tests for each ingester route.
- [ ] Add cross-user, cross-project, and cross-source tests for approved ingester operations.
- [ ] Add service-level and background-operation tests that bypass route dependencies.
- [ ] Confirm disabled operations cannot be invoked through direct application routes.

**Completion Criteria**

Focused ingester authorization tests cover application roles, resource checks, and disabled-operation behavior.

## Progress Tracker

| Area | Status | Notes |
|---|---|---|
| Route and operation classification | Not started | Authorization inventory required before enforcement |
| Application-role enforcement | Not started | Uses the centralized authorization policy |
| Approved-operation resource checks | Not started | Depends on containment requirements for each operation |
| Authorization validation | Not started | Requires cross-resource regression coverage |

## Definition Of Done

- [ ] Each ingester route and background operation has an explicit authorization requirement.
- [ ] Metadata requires an authenticated principal.
- [ ] Validation and execution require `operator`.
- [ ] Configuration and registration require `admin`.
- [ ] Approved operations authorize every source and destination before use.
- [ ] Operations without required authorization and containment checks remain disabled.
- [ ] Focused ingester authorization tests pass.

## Validation And Testing

- Test unauthenticated, unauthorized, and authorized access to each ingester route.
- Test operator and administrator application-role decisions.
- Test cross-user, cross-project, and cross-source access for approved operations.
- Test service and background-operation entry points without route dependencies.
- Test that disabled operations cannot be invoked.

## Deliverables

| Deliverable | Description | Status | Link |
|---|---|---|---|
| Ingester authorization inventory | Routes and background operations with required roles and resource checks | Not started | TBD |
| Authorization enforcement | Route, service, and operation checks for approved ingester capabilities | Not started | TBD |
| Authorization regression suite | Application-role and cross-resource ingester tests | Not started | TBD |

## Scope

**In scope**

- Authorization for the ongoing `sead_change_request` ingester proposal.
- Application-role checks for metadata, validation, execution, configuration, and registration.
- Resource authorization and containment prerequisites for approved ingester operations.

**Out of scope**

- Enabling an ingester capability before its source, project, database, destination, authorization, and containment checks are implemented.
- Replacing the centralized authorization policy or its stable principal contract.

## Assumptions

- The centralized authorization system remains the source of application-role decisions.
- The ingester feature remains an ongoing proposal; these tasks do not describe implemented behavior.

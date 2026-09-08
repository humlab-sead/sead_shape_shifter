# Proposal: Secure Ingester Filesystem Boundaries

## Status

- Proposed change
- Scope: `sead_change_request` ingester source and destination paths
- Goal: define and enforce approved filesystem boundaries before enabling unsafe ingester operations

## Summary

Defer ingester path hardening from Phase 2 to this focused proposal. The ingester is still under development, and its source, project, output, database, and temporary paths do not yet have one agreed operation contract. Keep affected operations disabled until those boundaries and their authorization checks are implemented.

## Problem

An ingester can read from or write to several resource types. Enabling an operation before each input and destination has an approved root could expose arbitrary files, overwrite unrelated project data, or bypass resource authorization.

## Scope

- Classify every ingester source, project, database, output, and temporary path.
- Define approved roots and containment checks for each operation.
- Require resource authorization before opening a source or creating a destination.
- Keep operations unavailable when a required boundary or authorization check is missing.
- Add regression tests for traversal, absolute paths, symlinks, cross-project references, and direct service invocation.

## Non-Goals

- Enabling new ingester capabilities without the required checks.
- Replacing the centralized authorization policy.
- Designing ingester transformation or submission-lifecycle behavior.

## Proposed Design

Use the shared containment guard for every filesystem path. Resolve symlinks before access, reject absolute and traversal paths unless an explicitly approved absolute root is being checked, and re-check the destination immediately before opening or creating it.

Each approved operation should receive authorized resource objects or validated paths from its route/service boundary. Direct service and background entry points must apply the same checks and must not rely on route dependencies. Operations that cannot satisfy these checks remain disabled.

## Testing And Validation

- Test unauthenticated, unauthorized, and authorized route access.
- Test traversal, absolute paths, symlink escapes, and cross-project references for every enabled file path.
- Test source and destination checks through service and background entry points.
- Confirm disabled operations cannot be invoked through HTTP or direct application calls.

## Acceptance Criteria

- Every ingester path has a documented approved root and authorization requirement.
- No enabled ingester operation can read or write outside its assigned root.
- Symlink and time-of-check/time-of-use cases are covered.
- Direct service invocation cannot bypass authorization or containment checks.
- Operations without complete checks remain disabled.

## Final Recommendation

Keep Work Area 4 deferred from Phase 2 and implement it through this proposal before enabling additional ingester operations.

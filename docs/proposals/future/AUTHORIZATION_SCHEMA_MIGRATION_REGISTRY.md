# Authorization Schema Migration Registry

## Status

- Future proposal / not yet approved
- Scope: authorization SQLite schema versioning and future migration registration
- Goal: keep future schema changes pluggable while removing unsupported historical migrations
- Related: [AUTHORIZATION.md](../../AUTHORIZATION.md), [OPERATIONS.md](../../OPERATIONS.md)

## Summary

Use a typed global migration registry for future authorization database schema changes. New databases should be created directly at the current schema version. The registry should apply only later, explicitly registered migrations in deterministic version order.

The current v1-to-v2 migration is not needed. No v1 authorization database has been deployed and v1 will not be supported. Existing databases below the current baseline should fail with an actionable error rather than being transformed by obsolete compatibility code.

## Problem

The repository currently creates a v1 authorization schema and immediately upgrades it through v2, v3, and v4 migrations. This preserves historical states that are not part of the supported deployment contract and makes the initial schema harder to read.

Future schema changes still need an explicit upgrade mechanism. Removing all version tracking would make later changes depend on manual database replacement or ad hoc startup logic.

## Scope

- Define the current authorization schema as the direct new-database baseline.
- Keep `schema_version` as the durable migration ledger.
- Add a typed global registry for future migrations.
- Register migrations by target schema version at import time.
- Apply pending migrations in ascending order, one transaction per migration.
- Reject unsupported databases below the current baseline.
- Add tests for registration, ordering, duplicate versions, gaps, failure handling, and fresh database creation.

## Non-Goals

- Supporting deployed v1, v2, or v3 authorization databases.
- Importing arbitrary migration plugins from the filesystem or Python environment.
- Changing authorization roles, grant semantics, audit behavior, or manifest application.
- Replacing the `sead-authorization migrate` command used to initialize the database and apply reviewed authorization manifests.
- Adding destructive automatic repair for unsupported databases.

## Current Behavior

`SQLiteAuthorizationRepository._migrate()` creates `schema_version`, creates the v1 table shape, and then upgrades the database through four schema versions. Version 2 replaces `grant_record.principal_id` with typed `subject_type` and `subject_id` fields. Versions 3 and 4 add audit subject and membership-review fields.

The current tests expect a fresh database to finish at schema version 4. No repository-supported deployment requires a pre-version-4 database.

## Proposed Design

### Baseline schema

Create the current schema directly for a new database:

- `resource` includes the self-referencing parent resource ID.
- `grant_record` starts with typed subjects.
- `application_role` stores deployment-wide roles.
- `audit_event` includes subject, provider, and details fields.
- `schema_version` records version 4 for the new database.

If an existing database reports a version below 4, repository initialization fails with a message instructing the operator to create a new authorization database. The error must not silently discard data.

### Migration registry

Provide a typed module-level registry owned by the authorization migration package. A migration registers a unique target version and receives a SQLite connection. The registry validates duplicate versions and returns pending migrations in numeric order.

Migration modules register through decorators when imported. The package imports supported migration modules explicitly so registration is deterministic and does not depend on filesystem scanning or arbitrary plugin discovery.

A migration runner should:

1. Read the current version.
2. Reject versions below the supported baseline.
3. Identify registered versions greater than the current version.
4. Reject missing intermediate versions.
5. Apply each migration in order in its own transaction.
6. Record the target version only after the migration succeeds.

The repository should import the migration package before running the migration runner. Future migrations begin at version 5.

### Separation of responsibilities

The repository migration runner changes database structure and data required by that structure. Manifest inspection and application remain in `authorization/operations.py`. They are data initialization and reconciliation operations, not schema migrations.

## Alternatives Considered

### Keep the current historical migrations

Rejected. They preserve unsupported deployment states and require new databases to pass through schema versions that no supported environment needs.

### Remove all schema versioning

Rejected. Future schema changes would lack a durable, ordered record and would be harder to validate and recover.

### Discover migration modules dynamically

Rejected. Filesystem or entry-point discovery would make startup behavior less predictable and could load migrations that were not intended for the deployed image.

### Hard-code every future migration in the repository

Deferred. A registry provides a smaller repository migration method and keeps each migration isolated, while retaining explicit imports and reviewable startup behavior.

## Risks And Tradeoffs

- Existing pre-version-4 local databases will require explicit replacement or a separately maintained conversion tool.
- A global registry depends on migration modules being imported; missing an explicit import can hide a migration until startup validation detects a version gap.
- One transaction per migration simplifies failure recovery but may require a retry after a failed deployment.
- SQLite schema changes remain single-host operations and must not be run concurrently by multiple application processes.

## Testing And Validation

- Create a fresh database and verify all current tables, columns, constraints, and indexes exist with schema version 4.
- Verify a pre-version-4 database fails with the documented unsupported-version error.
- Register test migrations and verify deterministic ordering and version recording.
- Reject duplicate migration versions and missing intermediate versions.
- Verify a failed migration does not record its target version.
- Verify repository startup remains idempotent for a current database.
- Run focused authorization tests and the full backend authorization test set.

## Acceptance Criteria

- `P-AC-1` A fresh authorization database is created directly at schema version 4 with the current table definitions.
- `P-AC-2` Unsupported databases below version 4 fail with an actionable error and are not modified.
- `P-AC-3` Future migrations can self-register under unique target versions in a typed global registry.
- `P-AC-4` Registered migrations run once, in ascending order, with version records written only after successful completion.
- `P-AC-5` Missing migration versions, duplicate registrations, and migration failures produce explicit errors.
- `P-AC-6` Manifest initialization and reconciliation remain separate from schema migration.
- `P-AC-7` Focused authorization tests and the backend authorization suite pass.

## Planning Handoff

- Preserve schema version 4 as the supported baseline.
- Preserve typed grants, audit fields, resource parent relationships, and manifest operations.
- Do not add dynamic migration discovery.
- Resolve registry import validation and unsupported-database error wording before implementation of the future registry phase.
- Expected validation includes fresh-schema inspection, unsupported-version failure, registry ordering, transaction failure behavior, and authorization regression tests.

## Recommended Delivery Order

1. Establish the direct version-4 baseline and remove obsolete v1-v3 upgrade code.
2. Add the typed registry and explicit migration package imports.
3. Add a representative version-5 test migration and runner validation.
4. Document the supported baseline and recovery procedure.

## Final Recommendation

Adopt schema version 4 as the only supported initial authorization database baseline and retain version tracking for future upgrades. Implement future schema changes through an explicitly imported, self-registering migration registry rather than historical compatibility branches or dynamic plugin discovery.

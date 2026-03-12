# Auto-Fix

## Feature Description

Auto-fix is a limited remediation feature in the backend that can generate and apply a small set of safe validation fixes after user confirmation.

It is intended to reduce repetitive cleanup for narrowly defined validation problems, not to replace normal validation review or manual project editing.

## Current Status

Status as of March 2026: limited backend capability, hidden in the current frontend UI.

- The validation panel no longer exposes the Auto-fix suggestion UI.
- The backend service still exists and can prepare or apply a restricted set of fixes.
- The feature should be treated as provisional rather than a primary workflow.

## Currently Supported Fixes

- Remove configured columns that do not exist in the source data.
- Fill null `system_id` values in fixed entities with sequential positive integers.
- Reassign duplicate `system_id` values in fixed entities to unique sequential values.
- Replace invalid `system_id` values in fixed entities when values are non-integer, zero, or negative.

## Not Currently Auto-Fixed

- Unresolved `@value:` references.
- Duplicate natural or business keys.
- Most structural configuration issues.
- Most foreign-key and source-data problems.

## Operational Notes

- Fixes are confirmation-based.
- Backup and rollback behavior is part of the backend flow.
- Any fix touching `system_id` values should be reviewed carefully because it can affect dependent relationships.
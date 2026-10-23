# Ingester Authorization — Merged

## Status

This proposal has been merged into [Security Hardening Follow-up](../SECURITY_HARDENING_FOLLOWUP/SECURITY_HARDENING_FOLLOWUP.md). That proposal is now the authoritative source for generic ingester authorization and containment requirements.

## Summary

The merged proposal records the removal of the path-based `sead` ingester under [issue #569](https://github.com/humlab-sead/sead_shape_shifter/issues/569), preserves the project-only Change Request authorization exception, and requires resource-specific authorization before any future generic-route ingester is enabled.

The original planning questions about project scope, approved resource references, and registration behavior are carried into the Security Hardening Follow-up handoff. Use that proposal for future decisions and implementation planning.

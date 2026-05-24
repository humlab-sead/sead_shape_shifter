# SEAD Change Request Ingester

## Overview

This folder contains the current proposal and Delivery 1 implementation-planning material for replacing the existing SEAD Clearinghouse ingester with a new `sead_change_request` ingester.

The accepted Delivery 1 direction is:

- DataFrame-first ingestion inside the ingester core
- identity resolution before SQL generation
- SIMS allocation for new entities and allocatable classifiers
- reconciliation-first handling for existing classifier matches
- forward-only change-package generation with non-revertible placeholder handling when required

## Documents

- [SEAD_CHANGE_REQUEST_INGESTER.md](./SEAD_CHANGE_REQUEST_INGESTER.md) — Current proposal and accepted Delivery 1 design decisions
- [DELIVERY_1_IMPLEMENTATION_PLAN.md](./DELIVERY_1_IMPLEMENTATION_PLAN.md) — Delivery 1 implementation plan, workstreams, and issue breakdown

## Current Status

- Proposal status: ready for Delivery 1 implementation planning
- Ingester key: `sead_change_request`
- Delivery 1 input contract: DataFrame-first, with adapter boundary only if framework compatibility requires it
- Delivery 1 confirmation model: synchronous at the change-package boundary; manual confirmation blocks artifact generation and returns a pending confirmation report

## Delivery 1 Scope Snapshot

- existing entity rows remain reference-only when `public_id` is populated
- bridge and association rows are evaluated independently using metadata-defined uniqueness rules where available
- classifier rows try reconciliation first and may allocate through SIMS in Delivery 1 if needed
- blocked unresolved rows stop the run before SQL generation
- collision checks cover target ID collisions plus metadata-defined bridge uniqueness checks

## Related References

- [Shape Shifter Design](../DESIGN.md)
- [Configuration Guide](../CONFIGURATION_GUIDE.md)
- [Developer Guide](../DEVELOPMENT.md)
- [Ingester System](../../backend/app/ingesters/README.md)

# SIMS Proposal Docs

This folder contains the proposal for **SIMS**: the SEAD Identity Management System.

SIMS is a separate SEAD-side system. It does not live inside Shape Shifter. The Shape Shifter SEAD ingester depends on SIMS through API calls for identity allocation and related lookup workflows.

## Documents

- [SEAD_IDENTITY_SYSTEM.md](./SEAD_IDENTITY_SYSTEM.md)
  Design and requirements for SIMS.

- [SEAD_IDENTITY_IMPLEMENTATION.md](./SEAD_IDENTITY_IMPLEMENTATION.md)
  Implementation-oriented material: schema, SQL functions, and API details.

- [SEAD_IDENTITY_NFR.md](./SEAD_IDENTITY_NFR.md)
  Non-functional requirements, security, operations, and testing.

## Boundary To Shape Shifter

- SIMS owns identity allocation, identity mappings, and the long-term basis for change detection.
- Shape Shifter owns normalization, reconciliation inputs, API client behavior, and SQL generation.
- The ingester should treat SIMS as an external dependency with a stable API contract.

## Related Docs

- [./new_ingester./SEAD_INGESTER_DESIGN.md](../SEAD_INGESTER_DESIGN.md)
  Shape Shifter ingester design that is an example of a system that consumes SIMS.

- [./aggregate_model/README.md](../../aggregate_model/README.md)
  Aggregate model documentation used by the SIMS proposal.
# Reconciliation Entity-Type Expansion

## Status

- Proposed feature — draft for review
- Scope: Extend the `site` reconciliation pilot to two additional local target entities and document how to add supported entity types.
- Goal: Confirm that the pilot workflow can support more than one entity shape without changing its identity and review rules.

## Summary

The reconciliation MVP defines an end-to-end workflow for `site`, but its scope does not include other local entities. The implementation is reported complete; manual end-to-end validation of the `site` workflow remains outstanding.

After that validation passes, this proposal recommends extending the same workflow to two additional local target entities and adding reconciliation-specific guidance to the developer guide. Select the two entities during phase planning after confirming that each has usable normalized rows, a stable business key, and a working remote matching type. A remote type listed by the matching service does not, by itself, mean a local target entity is supported.

## Problem

The MVP is explicitly limited to `site`. Developers have no reconciliation-specific guide for deciding whether another local entity is suitable, configuring its match fields, or verifying that exported links apply to the intended normalized rows. The general [Extending the System](../DEVELOPMENT.md#extending-the-system) section does not cover this workflow.

The specification distinguishes a local `entity_name` from the remote matching `service_type`. The editor loads remote types from the matching service manifest. Treating those remote types as proof that a local entity is ready for reconciliation could expose a type whose source rows, business keys, or end-to-end matching behavior have not been verified.

## Scope

- Extend the MVP workflow to two additional local entities in the target model, selected before phase task planning.
- For each selected entity, support candidate review, operator decisions, export to the mapping sidecar, and normalization using the same identity rules as the `site` pilot.
- Add a reconciliation section to `docs/DEVELOPMENT.md` that explains the prerequisites, configuration, and validation steps for adding another supported entity type.

## Non-Goals

- Enabling every local entity or every remote service type.
- Changing the MVP's decision states, business-key behavior, sidecar ownership, link precedence, or offline normalization.
- Automatically accepting candidates or changing Authority Service or SIMS identity policies.
- Adding audit history, multi-reviewer approval, rollback, or a new general plugin framework.
- Resolving existing-data adoption into SIMS. If it blocks validation for a selected entity, record that dependency before planning its end-to-end import.

## Current Behavior

- The [MVP proposal](./RECONCILIATION_MVP/RECONCILIATION_MVP.md) limits the first workflow to `site` and defines the key, review, export, normalization, and validation contracts to preserve.
- The project owner reports that implementation is complete apart from manual end-to-end validation. That validation has not yet cleared the MVP gate.
- The reconciliation editor obtains remote matching types from the service manifest, while the local entity is selected separately. Remote type availability does not establish complete support for a local entity.

## Proposed Design

### Gate on the site pilot

Before promoting support for other entities, manually validate the `site` match-to-normalization path against the MVP acceptance criteria. Confirm a real matching request and verify the resulting `public_id` and downstream foreign-key values. If the check fails, fix the pilot before expanding the supported entity set.

### Add a bounded first set

Select two non-`site` local target entities during phase planning. Each must:

- exist in the target model and produce normalized rows for a real project;
- have a stable, complete business key that can be represented by the entity's ordered sidecar `local_key`; and
- have a remote matching type that returns valid candidates for a real request.

For each entity, carry the MVP's reviewed-decision and export behavior through normalization. A candidate remains a suggestion until an operator acts. Exported links continue to use local business keys, and normalization continues to run without a network call.

Share the existing workflow where the entity contracts match. Add entity-specific configuration or handling only where a verified difference requires it. Do not make a local entity appear supported merely because a remote type is available in the service manifest.

### Document the extension process

Add a section to `docs/DEVELOPMENT.md` under **Extending the System**. Explain how to:

- check that a local entity and its normalized rows are suitable for reconciliation;
- identify and verify the local business key and remote matching type;
- configure the fields used for candidate search;
- run the review, export, and normalization workflow; and
- test the real match request, exported key, resulting `public_id`, and downstream foreign-key values.

Include one example from the first supported non-`site` entity and distinguish local entity names from remote matching-service types.

## Alternatives Considered

- **Enable all remote types immediately:** Rejected. A service manifest lists remote matching types; it does not prove that each local entity has compatible rows, keys, or complete workflow support.
- **Add entity-specific implementations without a shared guide:** Rejected. This would leave the next extension dependent on rediscovering the pilot's requirements and validation steps.
- **Build a generic plugin framework before adding the first types:** Rejected. The proposal has not established that the first two entities need an extension mechanism beyond the current configuration and service patterns.

## Risks And Tradeoffs

- Entity key shape, source data, and search fields may differ. The selected entities must be checked against the MVP's key contract before implementation.
- Live matching depends on the selected remote service type and usable database-backed data. Manifest or health checks alone do not prove that candidate matching works.
- Limiting the first expansion to two entities delays support for the rest of the target model but keeps validation and documentation focused.
- The MVP assessment records an unresolved SIMS adoption issue for existing rows. This proposal does not resolve that issue; the phase plan must keep it separate from validation of reconciliation and normalization unless a selected entity makes it a blocker.

## Testing And Validation

- Complete the manual `site` validation gate before promoting additional entity support.
- For each selected entity, run a real database-backed match request and verify the reviewed decision is keyed by the correct local business key.
- Verify that export writes the intended sidecar key, normalization sets the intended `public_id`, downstream foreign-key values are correct, and reruns preserve the result.
- Run the existing reconciliation regression tests to confirm that `site` behavior, manual-link precedence, and offline normalization remain unchanged.
- Have a developer follow the new guide using a selected non-`site` entity; verify that its configuration and validation steps match the implemented workflow.

## Acceptance Criteria

- `P-AC-1` The manual `site` validation confirms a real match request and the intended normalized `public_id` and downstream foreign-key values before support for other entities is promoted.
- `P-AC-2` Two named non-`site` local target entities complete candidate review, operator decision, export, and normalization using their ordered local business keys. Actual `public_id` and downstream foreign-key values match the reviewed decisions, and reruns without changes produce the same results.
- `P-AC-3` Each selected entity is validated with a real database-backed matching request; a health check or service manifest alone does not satisfy this criterion.
- `P-AC-4` The developer guide states the prerequisites and extension steps, distinguishes local entities from remote matching types, and includes a verified example for one supported non-`site` entity.
- `P-AC-5` Regression tests confirm the expansion does not change the MVP's operator-review requirement, sidecar key behavior, manual-link precedence, or offline normalization.

## Planning Handoff

**Confirmed decisions**

- The `site` MVP remains the reference contract for business keys, operator decisions, export, and normalization.
- Manual end-to-end validation of `site` is a gate; an unsuccessful check means the pilot must be corrected before promoting additional types.
- This proposal covers two additional local target entities, not every target-model entity or every remote service type.
- The developer guidance belongs in `docs/DEVELOPMENT.md`.

**Preserve**

- Use the ordered local business key for decisions and sidecar links; do not use `system_id` as an external identity.
- Matching proposes candidates but does not accept them.
- Keep normalization offline and preserve existing sidecar precedence.
- Do not equate remote matching-type availability with end-to-end support for a local entity.

**Validation**

- Verify actual matching requests, exported keys, normalized IDs, downstream references, and repeat-run results.
- Run the existing `site` regression tests alongside tests for both selected entities.
- Do not claim successful SIMS adoption unless that separate dependency is validated.

**Open questions**

- Which two local entities meet the target-model, key, source-data, and live matching requirements? Resolve before the phase plan is finalized.
- Is a disposable database-backed matching environment available for both selected types? Resolve before their implementation tasks are planned.
- Does either selected entity require SIMS adoption to validate its intended downstream use? Resolve before setting that entity's end-to-end validation scope.

## Final Recommendation

Approve a gated, two-entity expansion of the `site` reconciliation pilot and add a verified developer guide. Select the entities only after checking local model and live matching readiness, and preserve the MVP's key, review, export, and offline-normalization rules.

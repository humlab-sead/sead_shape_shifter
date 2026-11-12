# Direct Target-ID Conditional FK Conformance

## Status

- **Implemented**
- Scope: Project validation skips the reconciliation-pending issue for valid conditional direct-target-ID foreign keys while retaining the target-database ID check and independent target requirements.
- Goal: Do not require reconciliation to establish a lookup entity requirement when the foreign key uses an existing target ID.
- Validation: Not recorded in this proposal.

## Summary

Skip the conditional FK's awaiting-reconciliation result when the source entity validly declares `foreign_key_value_sources.<target>: public_id`. That relationship does not need a project lookup entity or Core link, even if source rows will be inserted. Continue to report the pending target-database check for the supplied IDs. Other relationships and independent requirements for the target entity remain in force.

Related decisions: [Conditional Target Model Requirements](../../done/CONDITIONAL_TARGET_MODEL_REQUIREMENTS/CONDITIONAL_TARGET_MODEL_REQUIREMENTS.md), [Direct Target-Id Foreign Keys](../../done/DIRECT_TARGET_ID_FOREIGN_KEYS/DIRECT_TARGET_ID_FOREIGN_KEYS.md), and [Direct Target-ID Foreign Key UX](../../DIRECT_TARGET_ID_FOREIGN_KEY_UX/DIRECT_TARGET_ID_FOREIGN_KEY_UX.md).

## Problem

Project-only conformance reports `CONDITIONAL_FK_AWAITING_RECONCILIATION` for every conditional FK whose source entity is present. It reports the same result when that FK is configured to supply an existing target ID directly. In this case, reconciliation cannot change whether a project lookup entity or Core link is needed: neither is needed for this relationship. The status suggests an unresolved dependency that the project does not have.

## Scope

- Make the conditional conformance result specific to each FK's valid value-source declaration.
- Preserve validation of the declaration, other reasons to require the target entity, and change-request checks for direct IDs.

## Non-Goals

- Changing `required_when` syntax or its insert-based timing for local `system_id` links.
- Changing ingestion, target-ID existence checks, or the entity editor.
- Exempting a referenced entity from an independent requirement imposed by the target model or another relationship.

## Current Behavior

The [conditional conformance validator](../../../../src/target_model/conformance.py) reports an informational awaiting-reconciliation issue for every conditional FK on a present source. The same module already checks whether a `public_id` declaration is a valid direct FK and separately reports `DIRECT_FK_TARGET_CHECK_PENDING`. The [change-request projection](../../../../ingesters/sead_change_request/target_projection.py) skips local FK projection for declared direct IDs; [direct-ID validation](../../../../ingesters/sead_change_request/direct_fk_validation.py) checks required values on inserted rows and verifies supplied IDs against the target database. An existing [conformance test](../../../../tests/model/test_target_model_conformance.py) explicitly expects both pending results for a conditional direct-ID FK.

## Proposed Design

For each conditional target-model FK, report `CONDITIONAL_FK_AWAITING_RECONCILIATION` only if that relationship does **not** have a valid direct `public_id` declaration on its source project entity. Reuse the existing conformance rule for identifying a valid direct declaration; do not infer direct-ID mode from the FK column or the absence of a project lookup entity.

Keep `DIRECT_FK_TARGET_CHECK_PENDING` for valid direct IDs. Do not suppress errors from an invalid declaration. If another source entity uses a local link to the same target, its own conditional status remains; a globally required target entity remains required.

## Risks And Tradeoffs

Suppressing the reconciliation status must not make an invalid direct-ID declaration appear valid or conceal a dependency from another FK. Applying the exception per relationship, after checking the declaration's validity, avoids both cases.

## Testing And Validation

Check project-only conformance with a valid conditional direct-ID FK, a local/default `system_id` FK, an invalid direct-ID declaration, two sources referencing the same target in different modes, and an independently required target. Confirm direct-ID pending checks remain and change-request validation still rejects missing required values or nonexistent target IDs on inserted rows.

## Acceptance Criteria

- `P-AC-1` A valid conditional direct-ID FK produces `DIRECT_FK_TARGET_CHECK_PENDING` but not `CONDITIONAL_FK_AWAITING_RECONCILIATION`; omitting its otherwise optional project target and Core link does not cause a requirement error from that relationship.
- `P-AC-2` An undeclared or `system_id` conditional FK still reports awaiting reconciliation; an invalid `public_id` declaration retains its conformance errors rather than being treated as an exemption.
- `P-AC-3` A separate FK to the same target continues to report its own conditional result when applicable, and independently required target entities remain required.
- `P-AC-4` Change-request validation still requires a direct-ID value for selected inserts when `required_when` applies and rejects nonexistent supplied target IDs.

## Final Recommendation

Treat a valid direct target-ID declaration as satisfying only that conditional FK's need for a project lookup. Keep all other conformance and change-request checks unchanged.

# Manifest-Driven Reconciliation Inputs — Phase Plan

## Status

- Approved

## Summary

Sequence the [approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) from an Authority Service manifest contract through Shape Shifter editor compatibility, two configuration pilots, and grouped validation.

## Problem

The editor currently offers `defaultTypes` as if every type were implemented for reconciliation, uses hard-coded properties and a fallback list, and does not check saved mappings against current service metadata. A manifest-driven editor must first have an explicit supported-type contract and must preserve existing specifications when the manifest changes or fails.

## Scope

Cover the additive Authority Service manifest field, editor and matching eligibility, existing-specification compatibility, `feature_type` and `location` pilots, regression validation, and developer guidance. Keep matching in Authority Service. Do not include `taxon` implementation, SIMS adoption, change-request import, or materialization.

## Current Position

- The [proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) is approved and specifies `reconciliation.supportedTypes` separately from OpenRefine's `defaultTypes`.
- Phase 1 has added `reconciliation.supportedTypes` alongside `defaultTypes` and `extend.property_settings` in Authority Service source. On 2026-11-04, the service at `http://localhost:8024` returned `{"status":"alive"}`, a manifest with 10 supported IDs (including `feature_type` and `location`), zero properties for `feature_type`, and `place_name` for `location`; read-only match requests returned two `feature_type` and one `location` candidates. These checks establish availability for that deployed local service, not staging deployment or the separate minimal-role `location` read grant.
- Shape Shifter's specification editor reads `defaultTypes`, has hard-coded per-type properties and a fallback list, and displays saved mapping keys without checking their current support.
- The `site` MVP is recorded as implemented in the source proposal. Its live checks for the two new types are reported there, not rerun for this plan. The proposal records missing business keys for the pilot entities and a separate schema-read-grant fix in progress.

## Phase Plan

### Phase 1: Publish a Reconciliation-Specific Manifest Contract

**Goal**

Make Authority Service publish implemented reconciliation types and accurate property declarations without changing the existing OpenRefine contract.

**Focus**

- Add the supported-type declaration separately from `defaultTypes`; exclude types without implemented matching, including `taxon` unless its implementation is confirmed.
- Define and verify valid type/property metadata, including a supported type with zero properties.
- Verify real candidate requests and schema read access for the pilot types; identify any remaining deployment-access blocker rather than treating a healthy manifest as proof of working matches.

**Depends On**

- The approved source proposal's additive manifest contract.

**Outputs**

- A manifest contract usable by Shape Shifter, with supported-type and property behavior verified against real matching.

**Acceptance Criteria**

- `PH1-AC-1` (from `P-AC-2`) The published supported IDs each identify a type in `defaultTypes`; the existing OpenRefine type list remains available and property declarations match the types they serve.
- `PH1-AC-2` (from `P-AC-3`) A valid zero-property supported type remains distinguishable from missing or malformed required metadata.
- `PH1-AC-3` (from `P-AC-5`) Real database-backed requests return candidates for `feature_type` and `location` with the service's deployment access in place.

**Validation Milestones**

- `VM-1` Contract and OpenRefine compatibility checks cover `PH1-AC-1` and `PH1-AC-2`.
- `VM-2` Real candidate requests and read-access checks cover `PH1-AC-3`; record any deployment blocker explicitly.

**Task-Plan Handoff**

- Use `P-AC-2`, `P-AC-3`, and `P-AC-5`. Preserve the existing OpenRefine fields. Confirm which registered strategies have implemented matching before publishing their IDs; a manifest response alone cannot establish database availability.

**Readiness**

Ready for a task plan.

### Phase 2: Consume the Contract Without Losing Saved Mappings

**Goal**

Replace hard-coded editor options while keeping existing specifications intact and preventing unverified matching.

**Focus**

- Offer only supported types and properties declared for the selected type; remove built-in fallbacks.
- Show manifest errors separately from a valid zero-property type, and retain saved types and mappings through load, save, type changes, and outages.
- Flag unsupported mappings for explicit removal or remapping before matching; enforce eligibility in the backend for saved, YAML, and API-driven specifications, including candidate search and suggestions; preserve working `site` configuration.

**Depends On**

- Phase 1's supported-type and property contract.

**Outputs**

- An editor and matching path that consume the manifest, preserve saved values, and report unsupported or unverifiable configurations.

**Acceptance Criteria**

- `PH2-AC-1` (from `P-AC-2`) The editor offers only supported types and their declared properties, with no hard-coded per-type property defaults.
- `PH2-AC-2` (from `P-AC-3`) An unavailable or malformed manifest gives a visible error and no fallback, while a valid zero-property type remains usable.
- `PH2-AC-3` (from `P-AC-9`) Opening, saving, or changing the type of an existing specification does not silently erase mappings; unsupported or unverifiable mappings cannot be used for matching until resolved.

**Validation Milestones**

- `VM-3` Manifest-driven editor and failure-state checks cover `PH2-AC-1` and `PH2-AC-2`.
- `VM-4` Existing-specification, type-change, outage, and backend matching/suggestion checks cover `PH2-AC-3`.

**Task-Plan Handoff**

- Use `P-AC-2`, `P-AC-3`, and `P-AC-9`. Preserve saved values even when matching is blocked. The backend checks manifest availability, supported type, and declared property IDs before candidate requests from both matching routes or suggestions, including previously saved, YAML, and API-driven specifications. Editor checks provide early feedback but are not the enforcement point. Do not block opening or saving unchanged legacy values; preserve the existing disabled behavior when no service type is configured. A valid zero-property type remains eligible.

**Readiness**

Ready for a task plan. The enforcement decision is recorded above, and the Phase 1 contract is available at the checked local service. Verify the contract and candidate access again in each environment used for integration validation.

### Phase 3: Validate Label-Only Reconciliation

**Goal**

Prove the generic path works for `feature_type`, which has no service properties.

**Focus**

- Declare a stable local business key for the pilot configuration.
- Verify candidate review, operator decision, sidecar export, normalization, and an unchanged rerun without property mappings.
- Check that the parent receives the target ID in `public_id` while Core child foreign keys retain the parent's local `system_id`.

**Depends On**

- Phases 1 and 2, including manifest availability and matching eligibility.
- Selection of a stable business key for the `feature_type` pilot.

**Outputs**

- A verified zero-property pilot and reusable validation for the identity and rerun rules.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-5`) A real `feature_type` request returns candidates without property mappings.
- `PH3-AC-2` (from `P-AC-4`) Reviewed decisions export by the local business key; normalization and an unchanged rerun produce the intended parent `public_id` and unchanged local `system_id` child links.

**Validation Milestones**

- `VM-5` Database-backed classifier matching covers `PH3-AC-1`.
- `VM-6` Review-to-normalization and rerun checks cover `PH3-AC-2`.

**Task-Plan Handoff**

- Use `P-AC-4` and `P-AC-5`. Choose and verify the actual business key before authoring the task plan. Keep candidate acceptance manual and normalization offline.

**Readiness**

Requires a named decision: select and verify the `feature_type` pilot's business key.

### Phase 4: Validate Property Mapping Without a Type-Specific Client Change

**Goal**

Show that `location` can be added after the generic work through configuration and verification alone.

**Focus**

- Declare a stable local business key and map `place_name` from the service manifest to a local column.
- Verify candidate review, decision, export, normalization, and an unchanged rerun without adding a `location`-specific editor rule.
- Compare the resulting parent target ID and child Core links with the Phase 3 identity contract.

**Depends On**

- Phases 1 and 2 for the generic manifest-driven path; Phase 3 for the identity validation reference.
- Selection of a stable business key and property source for the `location` pilot.

**Outputs**

- A verified property-assisted pilot demonstrating configuration-only expansion beyond `site`.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-6`) `location` is configured with the manifest-declared `place_name` property without a type-specific Shape Shifter code change.
- `PH4-AC-2` (from `P-AC-5`) A real database-backed `location` request returns candidates.
- `PH4-AC-3` (from `P-AC-4`) Review, export, normalization, and an unchanged rerun preserve the intended parent target ID and local `system_id` child links.

**Validation Milestones**

- `VM-7` Configuration-only property mapping and live matching cover `PH4-AC-1` and `PH4-AC-2`.
- `VM-8` Identity and rerun checks cover `PH4-AC-3`.

**Task-Plan Handoff**

- Use `P-AC-4`, `P-AC-5`, and `P-AC-6`. Choose the `location` business key and source column before planning implementation. Do not count the generic manifest change from Phase 2 as a type-specific edit.

**Readiness**

Requires a named decision: select and verify the `location` business key and `place_name` source column.

### Phase 5: Validate Grouped Parity and Document Configuration

**Goal**

Confirm the new pilots do not regress `site` or the MVP's review and identity rules, and publish accurate configuration guidance.

**Focus**

- Run grouped `site`, `feature_type`, and `location` regressions with disposable database-backed data.
- Verify operator review, business-key sidecar links, manual-link precedence, offline normalization, parent `public_id` and child `system_id` behavior.
- Document supported-type selection, properties, business keys, real match checks, saved-mapping recovery, and visible manifest failures; perform a read-only deployed-service smoke check without writing to shared project sidecars.

**Depends On**

- Phases 3 and 4, and deployment read access verified in Phase 1 or explicitly resolved before the smoke check.

**Outputs**

- Grouped regression results, read-only smoke results, and developer guidance aligned with the implemented behavior.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-1`, `P-AC-8`) The `site` workflow and MVP review, sidecar precedence, and offline-normalization rules remain unchanged.
- `PH5-AC-2` (from `P-AC-4`) Both pilot outcomes remain identical on unchanged reruns, including target IDs on parent `public_id` columns and local `system_id` Core child links.
- `PH5-AC-3` (from `P-AC-7`) The developer guide describes the implemented configuration procedure with a working type pair and explains what a manifest declaration does not prove.

**Validation Milestones**

- `VM-9` Grouped regression against the MVP behavior covers `PH5-AC-1` and `PH5-AC-2`.
- `VM-10` Guide walkthrough and read-only deployed-service smoke check cover `PH5-AC-3` and confirm candidate requests without changing shared sidecars.

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-4`, `P-AC-7`, and `P-AC-8`. Keep the MVP validation record intact; do not extend acceptance into SIMS import or change-request packaging.

**Readiness**

Requires a named decision if deployed read access remains unavailable after Phase 1: resolve that blocker before the read-only smoke check. Task planning also depends on both pilot results.

## Cross-Phase Rules

- Preserve the OpenRefine fields while adding reconciliation-specific metadata; an implemented type is not proof of working database access.
- Do not silently discard existing specification values or run matching with unsupported or unverified mappings.
- Keep decisions keyed by local business keys, target IDs on parent `public_id` columns, Core child links on local `system_id`, and normalization offline.
- Validate the zero-property case and property-assisted case separately before grouped promotion.

## Validation Strategy

- Contract checks in Phase 1 establish supported-type and property metadata, zero-property semantics, and real candidate availability (`VM-1`, `VM-2`).
- Editor and compatibility checks in Phase 2 establish valid options, explicit errors, and preservation of existing mappings (`VM-3`, `VM-4`).
- Disposable database-backed pilot checks in Phases 3–4 establish reviewed decisions, correct IDs, and repeatability (`VM-5`–`VM-8`).
- Grouped regressions and a read-only deployed-service smoke check in Phase 5 confirm MVP parity and usable guidance (`VM-9`, `VM-10`).

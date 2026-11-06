# Manifest-Driven Reconciliation Inputs — Phase Plan

## Status

- Approved

## Summary

Sequence the [approved proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) from an Authority Service manifest contract through Shape Shifter editor compatibility, two mocked workflow pilots, and grouped validation.

## Problem

The editor currently offers `defaultTypes` as if every type were implemented for reconciliation, uses hard-coded properties and a fallback list, and does not check saved mappings against current service metadata. A manifest-driven editor must first have an explicit supported-type contract and must preserve existing specifications when the manifest changes or fails.

## Scope

Cover the additive Authority Service manifest field, editor and matching eligibility, existing-specification compatibility, mocked `feature_type` and `location` workflow tests, regression validation, and developer guidance. Keep matching in Authority Service. Do not include multilingual matching strategies, `taxon` implementation, SIMS adoption, change-request import, or materialization.

## Current Position

- The [proposal](MANIFEST_DRIVEN_RECONCILIATION_INPUTS.md) is approved and specifies `reconciliation.supportedTypes` separately from OpenRefine's `defaultTypes`.
- Phase 1 has added `reconciliation.supportedTypes` alongside `defaultTypes` and `extend.property_settings` in Authority Service source. On 2026-11-04, the service at `http://localhost:8024` returned `{"status":"alive"}`, a manifest with 10 supported IDs (including `feature_type` and `location`), zero properties for `feature_type`, and `place_name` for `location`; read-only match requests returned two `feature_type` and one `location` candidates. These checks establish availability for that deployed local service, not staging deployment or the separate minimal-role `location` read grant.
- Shape Shifter's specification editor reads `defaultTypes`, has hard-coded per-type properties and a fallback list, and displays saved mapping keys without checking their current support.
- The `site` MVP is recorded as implemented in the source proposal. Phase 1's real service checks are separate from the deterministic Shape Shifter workflow tests planned for Phases 3 and 4.
- No real provider dataset is selected for Phase 3. Use synthetic provider-shaped rows with a fixture-only local key, separate from the search label; do not use the Arbodat test fixture or target-model uniqueness as evidence for a real provider key.

## Phase Plan

### Phase 1: Publish a Reconciliation-Specific Manifest Contract

**Goal**

Make Authority Service publish implemented reconciliation types and accurate property declarations without changing the existing OpenRefine contract.

**Focus**

- Add the supported-type declaration separately from `defaultTypes`; exclude types without implemented matching, including `taxon` unless its implementation is confirmed.
- Define and verify valid type/property metadata, including a supported type with zero properties.
- Verify real candidate requests and schema read access for the pilot types as Authority Service checks; identify any remaining deployment-access blocker rather than treating a healthy manifest as proof of working matches.

**Depends On**

- The approved source proposal's additive manifest contract.

**Outputs**

- A manifest contract usable by Shape Shifter, with real service availability evidence recorded separately from client workflow tests.

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

Ready for a task plan. Use test doubles for deterministic Shape Shifter workflow tests; keep any live-service verification read-only and separate from those tests.

### Phase 3: Validate Label-Only Reconciliation

**Goal**

Prove the generic path works for zero-property `feature_type` using synthetic provider-shaped rows and mocked Authority Service responses.

**Focus**

- Use a fixture-only provider key that is distinct from the search label; do not select a real provider's business key in this phase.
- Use deterministic mocked responses to verify candidate review, operator decision, sidecar export, normalization, and an unchanged rerun without property mappings.
- Check that the parent receives the target ID in `public_id` while Core child foreign keys retain the parent's local `system_id`.

**Depends On**

- Phases 1 and 2 for manifest availability, matching eligibility, and the mocked client workflow.
- The approved use of synthetic provider-shaped rows and mocked service responses for Shape Shifter workflow validation.

**Outputs**

- Deterministic evidence that the zero-property client workflow preserves the provider key, target ID, and local child links across reruns. This does not claim a real provider key or Authority Service match quality.

**Acceptance Criteria**

- `PH3-AC-1` (from `P-AC-4`) A mocked zero-property `feature_type` request returns a deterministic candidate, and the accepted decision is exported under the fixture's local key.
- `PH3-AC-2` (from `P-AC-4`) Reviewed decisions export by the local business key; normalization and an unchanged rerun produce the intended parent `public_id` and unchanged local `system_id` child links.

**Validation Milestones**

- `VM-5` Mocked candidate review and decision export cover `PH3-AC-1`.
- `VM-6` Review-to-normalization and rerun checks cover `PH3-AC-2`.

**Task-Plan Handoff**

- Use `P-AC-4`. Define a fixture-only local key separately from the search label. Use a mocked manifest and deterministic candidate responses; keep candidate acceptance manual and normalization offline. Do not claim this fixture establishes a real provider key or matching quality.

**Readiness**

Ready for a task plan.

### Phase 4: Validate Property Mapping Without a Type-Specific Client Change

**Goal**

Show that `location` can be added after the generic work through configuration and verification alone.

**Focus**

- Use synthetic provider-shaped rows with a fixture-only key and a separate property source column; map `place_name` from a mocked manifest.
- Use deterministic mocked responses to verify candidate review, decision, export, normalization, and an unchanged rerun without adding a `location`-specific editor rule.
- Compare the resulting parent target ID and child Core links with the Phase 3 identity contract.

**Depends On**

- Phases 1 and 2 for the generic manifest-driven path; Phase 3 for the identity validation reference.
- Phase 1's real Authority Service availability check for `location` and Phase 2's manifest-driven path.
- The approved synthetic-fixture and mocked-service test approach.

**Outputs**

- Deterministic evidence that manifest-declared property mapping works without type-specific client code. This does not claim a real provider's key or Authority Service matching quality.

**Acceptance Criteria**

- `PH4-AC-1` (from `P-AC-6`) A mocked `location` manifest configures the declared `place_name` property without a type-specific Shape Shifter code change.
- `PH4-AC-2` (from `P-AC-4`) Mocked review, export, normalization, and an unchanged rerun preserve the intended parent target ID and local `system_id` child links.

**Validation Milestones**

- `VM-7` Mocked manifest configuration and property mapping cover `PH4-AC-1`.
- `VM-8` Mocked review, identity, sidecar, and rerun checks cover `PH4-AC-2`.

**Task-Plan Handoff**

- Use `P-AC-4` and `P-AC-6`. Define fixture-only keys and property columns in the task plan; do not treat them as real provider schema decisions. Do not count the generic manifest change from Phase 2 as a type-specific edit.

**Readiness**

Ready for a task plan. Define the fixture-only key and property source in the task plan; neither represents a real provider schema decision.

### Phase 5: Validate Grouped Parity and Document Configuration

**Goal**

Confirm the new pilots do not regress `site` or the MVP's review and identity rules, and publish accurate configuration guidance.

**Focus**

- Run grouped `site`, `feature_type`, and `location` workflow regressions with synthetic local fixtures and mocked Authority Service responses.
- Verify operator review, business-key sidecar links, manual-link precedence, offline normalization, parent `public_id` and child `system_id` behavior.
- Document supported-type selection, properties, provider-local business keys, saved-mapping recovery, and visible manifest failures. Keep real service checks separate and read-only; do not write to shared project sidecars.

**Depends On**

- Phases 3 and 4, and deployment read access verified in Phase 1 or explicitly resolved before the smoke check.

**Outputs**

- Grouped regression results, read-only smoke results, and developer guidance aligned with the implemented behavior.

**Acceptance Criteria**

- `PH5-AC-1` (from `P-AC-1`, `P-AC-8`) The `site` workflow and MVP review, sidecar precedence, and offline-normalization rules remain unchanged.
- `PH5-AC-2` (from `P-AC-4`) Both pilot outcomes remain identical on unchanged reruns, including target IDs on parent `public_id` columns and local `system_id` Core child links.
- `PH5-AC-3` (from `P-AC-7`) The developer guide describes the implemented configuration procedure with a working type pair and distinguishes mocked workflow tests from real service availability checks.

**Validation Milestones**

- `VM-9` Grouped regression against the MVP behavior covers `PH5-AC-1` and `PH5-AC-2`.
- `VM-10` A guide walkthrough covers `PH5-AC-3`; any deployed-service smoke check is separate, read-only, and does not gate mocked workflow acceptance.

**Task-Plan Handoff**

- Use `P-AC-1`, `P-AC-4`, `P-AC-7`, and `P-AC-8`. Keep the MVP validation record intact; do not extend acceptance into SIMS import or change-request packaging.

**Readiness**

Requires Phases 3 and 4 to complete. A staging smoke check is optional and is not a blocker for mocked workflow acceptance.

## Cross-Phase Rules

- Preserve the OpenRefine fields while adding reconciliation-specific metadata; an implemented type is not proof of working database access.
- Do not silently discard existing specification values or run matching with unsupported or unverified mappings.
- Keep decisions keyed by local business keys, target IDs on parent `public_id` columns, Core child links on local `system_id`, and normalization offline.
- Use synthetic provider-shaped rows and mocked Authority Service responses for deterministic Shape Shifter workflow tests. Do not present fixture keys as real provider keys or mock responses as evidence of matching quality.
- Keep real database-backed candidate checks separate as evidence of Authority Service availability; Phase 1 records these checks for both pilot types.
- Keep multilingual and provider-specific matching strategies in Authority Service, outside this proposal's Shape Shifter workflow tests.
- Validate the zero-property case and property-assisted case separately before grouped promotion.

## Validation Strategy

- Contract checks in Phase 1 establish supported-type and property metadata, zero-property semantics, and real candidate availability (`VM-1`, `VM-2`).
- Editor and compatibility checks in Phase 2 establish valid options, explicit errors, and preservation of existing mappings (`VM-3`, `VM-4`).
- Mocked-service workflow checks with synthetic provider-shaped rows in Phases 3–4 establish reviewed decisions, correct IDs, and repeatability (`VM-5`–`VM-8`).
- Grouped mocked regressions in Phase 5 confirm MVP parity and usable guidance (`VM-9`, `VM-10`). A read-only deployed-service smoke check is separate and optional.

# Manifest-Driven Reconciliation Inputs

## Status

- Approved feature
- Scope: Make Shape Shifter derive implemented reconciliation types and their service properties from the OpenRefine manifest, so supporting a new entity type is configuration and verification rather than a Shape Shifter code change. Validate the client workflow on `feature_type` and `location` with mocked service responses; verify service availability separately.
- Goal: Offer only types and properties declared by the reconciliation contract. Keep deterministic client workflow tests separate from real service and database checks.

## Summary

The reconciliation MVP delivered a reliable `site` workflow. Its remaining limitation is not the workflow but the **input**: the specification editor takes remote types from the service manifest but takes service properties from a hard-coded per-type map. That map disagrees with the live service for every type checked, and for `location` it offers only invalid names. Expanding coverage therefore means editing Shape Shifter for each type, and the edits are already wrong.

Shape Shifter is the primary and currently only consumer of SEAD Authority Service. That makes the division of responsibility simple: the service publishes what it can match, Shape Shifter reads it, and where the manifest cannot express something Shape Shifter needs, the manifest or the service is changed rather than the client hard-coded.

The decision is to use an additive reconciliation-specific manifest field for implemented types, alongside the existing OpenRefine fields:

- `defaultTypes[].id` remains the OpenRefine type list. It may include a type that Authority Service does not implement for reconciliation.
- Authority Service adds `reconciliation.supportedTypes`, a list of IDs whose matching behavior is implemented. The editor offers this list, using matching `defaultTypes` entries for display names. Each supported ID must match exactly one `defaultTypes[].id`.
- Service properties come from `extend.property_settings`, filtered by exact membership of the selected type ID in each entry's `entity_types`.
- Adding a supported type becomes: select an ID in `reconciliation.supportedTypes`, map its served properties to local columns, declare the local business key, and verify one real match request. No per-type Shape Shifter code change is needed.
- The second pilot uses `feature_type` (a classifier that serves no properties) and `location` (which serves one). Both match today. `taxon` may remain in `defaultTypes` for OpenRefine, but is excluded from `reconciliation.supportedTypes` until its matching behavior is implemented.
- Matching stays in Authority Service. Shape Shifter never fuzzy-matches.

## Problem

Reconciliation coverage cannot grow without client edits, and the client's built-in values are wrong.

- **Types are manifest-driven; properties are not.** The editor loads remote types from the manifest but fills service-property rows from a hard-coded map ([SpecificationEditor.vue](../../../frontend/src/components/reconciliation/SpecificationEditor.vue)). A remote type outside that map yields no property rows at all.
- **The hard-coded map is wrong for every type it covers.** Checked against the live manifest on 2026-11-04:

  | Remote type | Editor offers | Service serves | Offered but not served |
  | --- | --- | --- | --- |
  | `site` | `latitude`, `longitude`, `description`, `country`, `region` | `place_name`, `latitude`, `longitude`, `country`, `national_id` | `description`, `region` |
  | `taxon` | `rank`, `kingdom`, `family` | `scientific_name`, `genus`, `species`, `family` | `rank`, `kingdom` |
  | `location` | `latitude`, `longitude`, `country` | `place_name` | all three |

- **`location` cannot be configured at all.** Every property the editor offers is unserved, and the one served property is not offered.
- **The manifest already carries what is missing.** Each `extend.property_settings` entry declares a `name` and the `entity_types` it applies to, so the correct per-type list is derivable from the same response the editor already fetches for the type list.
- **The type fallback is stale too.** When the manifest request fails the editor offers `site`, `taxon`, `location`, and `abundance`. The live manifest advertises 13 types and does not include `abundance`. A stale fallback produces specifications that cannot match.
- **The editor does not validate saved mappings against current metadata.** In edit mode, it displays existing `property_mappings` keys instead of the selected type's current service properties. A saved mapping can therefore remain visible after its property disappears or the remote type changes, without being identified as unsupported.

The effect is that "add an entity type" is a Shape Shifter code project rather than a configuration step, and the code it produces is not verified against the service.

## Scope

- Add and consume `reconciliation.supportedTypes` separately from OpenRefine's `defaultTypes`; derive service properties from a validated `extend.property_settings` array and replace the hard-coded per-type property map.
- Remove the stale type fallback; make an unavailable or incompatible manifest an explicit, visible state rather than a silent guess.
- Preserve saved specifications when metadata changes or is unavailable. Show unsupported saved types and property mappings, require explicit removal or remapping before matching, and never silently discard saved values.
- Validate the Shape Shifter workflow for `feature_type` and `location` with synthetic provider-shaped rows and mocked Authority Service responses: candidate review, operator decision, sidecar export, normalization, and an unchanged rerun.
- Give each fixture a provider-style local key that is distinct from its search label. This tests key-based decisions and sidecar links; it does not select a business key for a real provider.
- Change SEAD Authority Service where the manifest is insufficient for these needs, preferring manifest or service changes over client special cases.
- Rewrite the developer guidance from "how to add an entity type" to "how to consume the manifest when creating a reconciliation specification".

## Non-Goals

- Implementing additional Authority Service matchers such as `taxon`. If `taxon` is not implemented, that work needs a separate decision; `feature_type` covers the classifier case in this proposal.
- Any entity-specific matching logic in Shape Shifter, or a new plugin/strategy framework there.
- Changing the MVP's decision states, sidecar ownership and precedence, or offline normalization.
- Auto-accepting candidates or changing Authority Service or SIMS identity policy.
- Implementing or evaluating multilingual or provider-specific matching strategies. Those strategies remain in Authority Service and require separate service-side tests.
- Claiming support for a type whose manifest entry has not been verified by a real match request.
- OpenRefine-first ergonomics beyond keeping the OpenRefine-style contract intact.
- SIMS change-request import, adoption, or materialization. Acceptance ends at normalization.

## Current Behavior

- The [MVP proposal](../done/RECONCILIATION_MVP/RECONCILIATION_MVP.md) limits the workflow to `site` and defines the key, review, export, normalization, and validation contracts to preserve. It is implemented, and its Phase 7 validation including the manual UI review passed on 2026-11-04.
- Property mappings are optional at match time. The query builder sends `properties` only when the mapping is non-empty and passes `None` otherwise ([service.py](../../../backend/app/services/reconciliation/service.py)), so a label-only classifier needs no properties at all.
- In edit mode, `SpecificationEditor.vue` copies saved `property_mappings` and uses their keys as the displayed properties. It does not compare those keys with the current service metadata. On a type change or manifest outage, saved mappings can therefore be preserved without being shown as unsupported.
- The editor currently loads types from `defaultTypes` and falls back to a built-in list if that field is missing or the request fails.
- Live check on 2026-11-04 against the deployed `authority` schema and the service at `http://localhost:8024`:

  | Remote type | `POST /reconcile` | Meaning |
  | --- | --- | --- |
  | `feature_type` | HTTP 200, real candidates (`Trench` → id 25 at 100%, `Post hole` → id 26 at 100%, `Roof` → id 29 at 100%) | Works end to end; serves no properties. |
  | `location` | HTTP 200, real candidates (`Sweden` → id 205, `Uppsala` → id 4233, both 100%) | Works end to end; serves `place_name`. |
  | `site` | HTTP 200 with real candidates | Works end to end; the MVP pilot. |
  | `taxon` | Reported HTTP 200 with `{"result":[]}` for names present in the data | The reported check returned no candidates. Confirm implementation status in Authority Service before including `taxon` in `reconciliation.supportedTypes`. |

- The local entities `feature_type` and `location` already exist in real projects as `type: fixed` with `public_id` set, but both declare `keys: []`, which blocks mapping operations until a business key is declared.
- Schema read access for non-owner roles was missing in the deployment tooling and is being added separately; before that fix every `site` and `location` request failed with `permission denied for schema authority`.

## Proposed Design

### Treat the manifest as the reconciliation input contract

The manifest must distinguish OpenRefine types from types implemented for reconciliation.

- `defaultTypes` remains the OpenRefine type list. It must be an array of objects with unique, non-empty string `id` values; the editor uses `name` when present and otherwise displays the ID. Its presence does not mean that every listed type can be reconciled.
- Authority Service adds `reconciliation.supportedTypes`, an array of unique, non-empty type IDs implemented by its reconciliation endpoint. Every ID must match exactly one `defaultTypes[].id`. An empty array is valid and means no types are implemented; a missing or malformed field is a manifest contract error.
- `extend.property_settings` must be present as an array. Every entry must have a non-empty string `name` and an `entity_types` array of non-empty string IDs. The editor selects properties only when the selected type ID exactly matches an ID in `entity_types`. Missing or malformed property metadata is a contract error, not an empty property list.
- A supported type with no matching property entries has a valid empty property list. This is how `feature_type` is represented; it is distinct from missing or malformed metadata.

The supported-type list records implemented matching behavior, not database availability or a guarantee that every request returns candidates. A real match request remains necessary to verify the configured service and data.

The manifest does **not** define which local entity maps to which remote type, which local column is the search label, or which local column feeds each property. Those remain specification choices and verification responsibilities.

### Derive types and properties in the editor

- Populate the remote-type list from `reconciliation.supportedTypes`, using the corresponding `defaultTypes` entry for its display name.
- Populate property rows from a valid `extend.property_settings` array, filtered by exact type-ID membership, replacing the hard-coded map.
- Keep property mappings optional: a classifier type such as `feature_type` legitimately serves none, and the specification must still run.
- Treat missing or malformed required metadata as a manifest error. A valid type with no matching property entries has no properties; it is not an error.
- Remove the hard-coded type fallback. When the manifest is unavailable or invalid, show the error and do not claim that saved types or mappings are valid.

### Preserve saved specifications

- When loading a saved specification, retain every `property_mappings` key and value. Merge the saved values with the current type's manifest properties; do not replace one set with the other.
- Show saved mapping keys that are not declared for the selected supported type as unavailable. Preserve them on save until an operator explicitly removes or remaps them.
- Changing the remote type must not silently delete mappings. Mark keys not declared for the new type as unavailable and require explicit removal or remapping before matching.
- If the manifest is unavailable or invalid, preserve the saved type and mappings, show that their compatibility is unknown, and prevent matching until the manifest can validate them. Saving an unchanged specification must not erase its values.

### Validate on two new entity types

- `feature_type` — a classifier with no properties. Confirms the label-only path and that a type serving no properties is usable rather than looking broken.
- `location` — one property, `place_name`. Confirms that a served property can be mapped to a local column and that offering only served properties is sufficient.

For Shape Shifter workflow tests, use synthetic provider-shaped rows and deterministic mocked Authority Service responses. Keep the provider-local key separate from the search label. Verify candidate review, operator decision, sidecar export, normalization that writes the intended target ID to the parent's `public_id`, child Core foreign keys that retain the parent's local `system_id`, and an unchanged rerun. These tests do not establish a real provider's business key or matching quality. Verify real Authority Service candidate availability separately under `P-AC-5`.

### Change Authority Service where the manifest is insufficient

Because Shape Shifter is the only consumer, the service can be adjusted instead of worked around:

- Ensure each advertised type declares its served properties completely and correctly, so the manifest is a reliable input.
- Publish `reconciliation.supportedTypes` separately from `defaultTypes`. Include a type only when its reconciliation matching behavior is implemented; do not use database availability or candidate count to define this list.
- Keep the required manifest fields and shapes explicit. A valid empty property list differs from absent or malformed `extend.property_settings`.
- Make schema read access part of deployment, so a deployed schema is usable by the service role without a manual grant.
- Keep types that lack implemented matching out of `reconciliation.supportedTypes`, even if they remain in `defaultTypes`. Do not paper over them in Shape Shifter.
- Keep multilingual and provider-specific matching strategies in Authority Service. Shape Shifter consumes the advertised type and properties; this proposal does not add matching logic there.

Manifest changes should stay additive so the OpenRefine-style contract keeps working for any other client.

### Document the configuration procedure

Replace the "add an entity type" guidance in `docs/DEVELOPMENT.md` with the procedure that now applies:

- read `reconciliation.supportedTypes` and choose an implemented remote type; use `defaultTypes` only for its display name;
- confirm that the required property metadata is present and valid, then map only properties declared for that type;
- choose the local entity and its search field, and declare its business key;
- map served properties to local columns, or none for a classifier; explicitly resolve any saved mapping that is not supported for the selected type;
- run one real match request to confirm the type actually matches;
- review, export, and normalize; confirm the target ID is on the parent's `public_id` and child Core foreign keys still contain the parent's local `system_id`;
- add a regression test for the new specification.

Distinguish local entity names from remote types explicitly. Use a confirmed working local-entity/remote-type pair in the guide, and do not infer reconciliation support from names in `defaultTypes`.

### Build and test environment

Use synthetic provider-shaped rows and mocked Authority Service responses for deterministic Shape Shifter workflow and regression tests. Keep disposable database-backed requests as separate Authority Service availability checks; Phase 1 records real `feature_type` and `location` results. A read-only staging smoke test is optional deployment verification, not a prerequisite for mocked workflow tests. Do not write to shared project sidecars or require SIMS identity state or change-request import.

## Alternatives Considered

- **Keep the hard-coded property map and add entries per type:** Rejected. It preserves a per-type client edit, has already drifted from the service for every type it covers, and produced a `location` entry with no valid property.
- **Fetch properties by a second, per-type service call:** Rejected. The manifest already declares properties per type, so an extra round trip adds a failure mode without adding information.
- **Keep the stale type fallback:** Rejected. Offering `abundance`, which the service does not advertise, creates specifications that cannot match and hides a manifest outage behind a plausible list.
- **Implement `taxon` in Authority Service as part of this change:** Deferred. Confirm its implementation status before including it in `reconciliation.supportedTypes`; if it is not implemented, handle that work as a separate decision. `feature_type` provides a working classifier to validate the mechanism.
- **Use `defaultTypes` as the reconciliation support list:** Rejected. It is the OpenRefine type list and may include types without reconciliation implementations. An additive `reconciliation.supportedTypes` field keeps the two meanings separate without changing the OpenRefine list.
- **Enable every supported type for every project:** Rejected. A service implementation does not prove that a local entity has rows, a business key, or a usable search field.
- **Put matching in Shape Shifter:** Rejected. It duplicates service behavior and inverts the consumer relationship.

## Risks And Tradeoffs

- **Malformed metadata can be confused with a valid empty property list.** Require the property-settings array and validate its entries before deriving properties. A supported type with no matching entries is a valid zero-property type; absent or malformed metadata is an error.
- **Removing the fallbacks changes failure behavior.** With the service down or required metadata invalid, the editor cannot validate a saved specification for matching. It must show the error and preserve saved values rather than substituting a stale list or clearing mappings.
- **Existing specifications may contain obsolete mappings.** Preserve those values and mark them unsupported until an operator removes or remaps them. This avoids data loss but may require manual cleanup before those specifications can run.
- **`keys: []` blocks these entities today.** Both pilot entities need a declared business key before export. For a classifier, the natural key is the label or a code column; choosing it is part of the work and affects how decisions are keyed.
- **The pilot's second entity is a classifier.** `feature_type` validates configuration and normalization but not property-assisted matching. Keep `site` as the property-mapping regression reference.
- **Authority Service changes are now in scope.** That is deliberate and follows from Shape Shifter being the only consumer, but it means the change spans two repositories and the manifest format must stay additive for other clients.
- **The MVP assessment records an unresolved SIMS adoption issue.** It does not block matching, export, or normalization, and remains a prerequisite only if a later import is tested.
- **A manifest server without a database looks healthy.** The manifest is served without touching the database, so an unreadable or unconfigured schema can still yield a valid supported-type declaration. Only a real match request proves the configured type works with the database.
- **Core foreign keys and target IDs serve different purposes.** Reconciliation writes the target ID to the parent's `public_id`; normalized child Core foreign keys must continue to use the parent's local `system_id`. Target-ID substitution in change-request packages is outside this proposal.

## Testing And Validation

- Editor: with a stubbed manifest containing supported and unsupported `defaultTypes`, only IDs in `reconciliation.supportedTypes` are offered; only properties declared for the selected type appear.
- Manifest contract: missing or malformed `defaultTypes`, `reconciliation.supportedTypes`, or `extend.property_settings` produces a visible error; a valid supported type with no matching property entries remains usable with zero properties.
- Editor: with the manifest unavailable or invalid, saved types and mappings remain unchanged, compatibility is shown as unknown, and matching is blocked.
- Editor: a type declaring no properties, such as `feature_type`, still allows a specification and a match request.
- Editor: opening and saving an existing specification preserves all mapping keys and values; changing its type marks unsupported keys and requires explicit removal or remapping before matching.
- Live service check: real database-backed requests for `feature_type` and `location` return candidates. This verifies Authority Service availability, not Shape Shifter's workflow or matching quality.
- End to end: for both entities, synthetic provider-shaped rows and deterministic mocked responses exercise review → decision → export → normalization. The target ID must reach the parent's `public_id`, child Core foreign keys must retain the parent's local `system_id`, and an unchanged rerun must produce identical results.
- Regression: the `site` workflow, manual-link precedence, sidecar key behavior, and offline normalization are unchanged.
- Regression: no property is offered that the live manifest does not serve for that type.
- Guide check: a developer follows the new configuration procedure for one type and the steps match the implemented workflow.
- Optional deployment check: a read-only staging manifest and candidate smoke test, with no exports to shared project sidecars.

## Acceptance Criteria

- `P-AC-1` The `site` pilot remains implemented and unregressed, with its manual validation record still valid.
- `P-AC-2` The editor offers only IDs in `reconciliation.supportedTypes`, displays their matching `defaultTypes` names, and derives their properties from a valid `extend.property_settings` array using exact type-ID membership. No hard-coded per-type property defaults remain in Shape Shifter.
- `P-AC-3` An unavailable manifest or missing or malformed `defaultTypes`, `reconciliation.supportedTypes`, or `extend.property_settings` produces a visible error and no fallback. A valid type with no matching property entries remains usable with zero properties.
- `P-AC-4` For `feature_type` and `location`, normalization writes the intended target ID to the parent row's `public_id`, child Core foreign keys contain that parent's local `system_id`, and an unchanged rerun produces identical results.
- `P-AC-5` Both entities return valid candidates from real database-backed requests, including one classifier type that declares no properties.
- `P-AC-6` After the generic manifest support is implemented, configuring `location` as an additional type beyond the `site` MVP requires no type-specific Shape Shifter code change; its `place_name` mapping works in a mocked-service workflow. Real service availability is verified separately under `P-AC-5`.
- `P-AC-7` The developer guide documents the configuration procedure, uses a working local-entity/remote-type pair, and states what a manifest entry does and does not prove.
- `P-AC-8` Regression tests confirm the MVP's operator-review requirement, sidecar key behavior, manual-link precedence, and offline normalization are unchanged.
- `P-AC-9` Opening and saving an existing specification preserves every saved mapping key and value. Changing its type marks unsupported mappings and requires explicit removal or remapping before matching; a missing or invalid manifest does not erase saved values and prevents matching.

## Planning Handoff

**Confirmed decisions**

- `reconciliation.supportedTypes` is the authoritative list of implemented reconciliation types; `defaultTypes` remains the OpenRefine list and is not a support guarantee.
- A valid `extend.property_settings` array is required. A supported type with no matching property entries is a valid zero-property type.
- Supporting a new entity type is configuration plus verification, not a Shape Shifter code change.
- The second and third pilots are `feature_type` and `location`. Keep `taxon` out of `reconciliation.supportedTypes` until its implementation is confirmed; the reported empty result alone does not establish support.
- Matching and type-specific search stay in Authority Service; Shape Shifter consumes advertised types and properties.
- Shape Shifter workflow tests use synthetic provider-shaped rows and mocked service responses. These tests verify client behavior, not a real provider's key or Authority Service matching quality.
- Real database-backed requests verify Authority Service availability separately; they are not required for every client workflow test.
- Shape Shifter is the primary consumer, so Authority Service and the manifest may be changed to fit its needs. Manifest changes stay additive.
- With no valid manifest, new configuration shows an explicit error and no fallback list; saved values remain visible but unverified.
- Existing mappings are preserved across load, save, type changes, and manifest outages; unsupported mappings must be explicitly removed or remapped before matching.
- Acceptance ends at normalization; SIMS import and adoption stay out.

**Preserve**

- Use the entity's declared business key for decisions and sidecar links; do not use `system_id` as an external identity.
- Write the target ID to the parent's `public_id`; keep Core child foreign keys on the parent's local `system_id`. Do not include change-request target-ID substitution in normalization acceptance.
- Matching proposes candidates but never accepts them; normalization stays offline and keeps existing sidecar precedence.
- Do not equate an advertised type or property with verified end-to-end support.
- Keep the OpenRefine-style contract intact for any other client.

**Validation**

- Confirm the supported-type list and served properties from the live manifest, and audit property declarations once at the service where they look incomplete.
- Test missing and malformed manifest fields separately from a valid type with no properties.
- Test that existing specifications retain mappings when opened, saved, changed to another type, or loaded during a manifest outage.
- Prove Authority Service support with real database-backed match requests; the manifest alone is not evidence.
- Confirm fixture-local keys for `feature_type` and `location` support sidecar export and an unchanged rerun. Do not present a synthetic fixture key as a real provider's business key.
- Keep `site` as the property-mapping regression reference, because `feature_type` declares no properties.

Do not include change-request import or SIMS adoption in this proposal's acceptance results.

## Final Recommendation

Approve the reframe: Authority Service should publish implemented reconciliation types separately from OpenRefine's `defaultTypes`, and Shape Shifter should use that list plus validated property metadata. Preserve saved mappings and require explicit cleanup before matching when the manifest no longer supports them. Test the Shape Shifter workflow for `feature_type`, a zero-property classifier, and `location`, which serves `place_name`, with synthetic provider-shaped rows and mocked service responses. Keep real service availability checks separate from those workflow tests. Keep multilingual and provider-specific matching strategies in Authority Service. Keep target IDs on parent `public_id` columns and Core child foreign keys on local `system_id` values. Keep manifest changes additive so the OpenRefine contract continues to serve other clients.

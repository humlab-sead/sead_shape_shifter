# Proposal: Increase Machine-Readable Fidelity Of BugsCEP Reconciliation Policies

## Status

- In progress
- Scope: extend the BugsCEP reconciliation policy schema so more importer behavior can be represented as executable policy data instead of helper names and comments
- Goal: make the policy files a closer machine-readable model of Java runtime behavior, starting with the patterns already exposed by `datescalendar.policy.yml`, `datesperiod.policy.yml`, and `datesradio.policy.yml`
- Implemented so far: direct related-output references, structured resolvers, grouped postprocess merge stages, shared `emit` blocks, initial `known_divergences` support, fixture-backed scenario validation, shared result-object comparisons against current Java behavior, and narrow policy-side execution for resolver, postprocess, ordered-reconciliation, supporting-output, and related-output graph slices

## Summary

This proposal recommends continuing the current incremental schema-extension pass after the importer inventory work.

The current policy format is strong at source mapping, ordered reconciliation, and several child-table patterns. It is weaker at structured helper behavior, parent-child identity flow, batch merge logic, and emitted runtime outcomes.

The first pass of those schema additions is now in place. The next step is to keep extending validation and execution coverage with the same narrow, shared-result approach instead of adding more helper labels and prose comments.

## Problem

The current policies describe a lot of the Java importer structure, but some important business logic is still not machine-readable enough to execute or validate directly.

Current gaps:

- child or supporting rows can be modeled in `related_outputs`, but the parent row still often receives the same child identity through a separate helper call
- helper-heavy logic such as dating-lab resolution is still represented as one named helper instead of ordered lookup behavior with fallback rules and emitted outcomes
- batch behavior such as the calendar-date range merge is still mostly described in prose even though it changes the persisted result
- row outcomes such as flagged rows, ignored items, and structured error reasons are not first-class policy data
- there is no standard way to record that a policy intentionally matches the current Java runtime even when the Java behavior is surprising or flawed

That means the policies are useful for review and code generation scaffolding, but not yet a full executable model of the Java importers.

## Scope

This proposal covers:

- schema changes for child identity references
- schema changes for structured resolver behavior
- schema changes for batch or postprocess merge behavior
- schema changes for machine-readable emitted issues and flags
- a lightweight way to record known policy-versus-Java divergences
- a validation approach that uses representative policies as the first proving ground

## Non-Goals

This proposal does not attempt to:

- replace the existing policy files in one change
- redesign simple mapping or reconciliation sections that already work well
- build a full general-purpose workflow language
- remove helper functions entirely
- prove full parity across all importers before the schema additions are implemented

## Current Behavior

The current schema already supports:

- structured `source`, `target`, `mappings`, `reconciliation`, `update_detection`, and `dependencies`
- top-level `output` for one-to-many main-table expansion
- runnable `related_outputs` for child or supporting tables

That has been enough to capture several useful patterns, including generated child rows, cached supporting rows, cascade-created supporting rows, and insert-only child graphs.

The current limit is not breadth of coverage. The limit is that the most conditional behavior is still compressed into helpers and comments.

## Proposed Design

### 1. Add Direct Related-Output References

Let the parent row and sibling outputs reference the identity and mapped fields of a runnable `related_outputs` entry directly.

Add two schema features:

- `related_outputs[*].phase`: `before_parent|after_parent`
- `related.<output_name>.<field>` in the expression language

This removes the need to represent the same behavior twice, once as runnable child output and again as a helper that returns the child ID.

Example:

```yaml
related_outputs:
  - name: analysis_entity
    phase: before_parent
    table: tbl_analysis_entities
    ...

mappings:
  - target_field: analysis_entity_id
    type: integer
    nullable: true
    transform:
      type: expr
      expr: "related.analysis_entity.analysis_entity_id"
```

Use `before_parent` when the child or supporting row must exist before the parent row can be mapped. Use `after_parent` for true child rows that depend on the parent identity.

### 2. Add Structured Resolvers

Add a first-class `resolvers` section for logic that is currently hidden behind opaque helper calls.

Each resolver should support ordered steps, cache use, trace lookups, repository lookups, constant fallbacks, and emitted outcomes.

Example:

```yaml
resolvers:
  - name: dating_lab_from_code
    returns: entity_ref
    args: [lab_id]
    steps:
      - name: unknown_lab_shortcut
        when: "lab_id is None or lab_id.strip() == '' or lab_id == config.unknown_bugs_lab_identifier"
        action: database_query
        table: tbl_dating_labs
        where: "lab_id = :lab_id"
        bind:
          lab_id: "config.unknown_sead_lab_identifier"
        on_match: return_entity
      - name: trace_lookup
        action: trace_lookup
        bugs_table: TLab
        identifier_expr: "lab_id"
        on_match: return_entity
      - name: direct_lookup
        action: database_query
        table: tbl_dating_labs
        where: "lab_id = :lab_id"
        bind:
          lab_id: "lab_id"
        on_match: return_entity
      - name: not_found
        action: emit_issue
        severity: error
        code: dating_lab_not_found
        message: "No lab found"
        return: empty_entity
```

This keeps reusable helper logic, but makes the runtime behavior visible to a machine.

### 3. Add Postprocess Merge Stages

Add a top-level `postprocess` section for batch or grouped behavior that happens after provisional row mapping but before final persistence.

This is needed for `datescalendar`, where rows are grouped by sample, then partitioned by dating method and note groups, then paired by uncertainty type, then possibly merged into one persisted row.

Example:

```yaml
postprocess:
  - name: merge_calendar_ranges
    phase: after_row_mapping_before_persist
    applies_to: target
    group_by:
      - "source.SampleCODE"
    partition_by:
      - "source.DatingMethod"
      - "normalized.notes_group"
    pair_rules:
      left: "normalized.uncertainty_kind in ['from', 'from_ca']"
      right: "normalized.uncertainty_kind in ['to', 'to_ca']"
    actions:
      - type: replace_field
        target: "target.relative_age_id"
        value: "resolver.calendar_range_relative_age(...)"
      - type: normalize_field
        target: "target.dating_uncertainty_id"
        value: "resolver.normalized_range_uncertainty(...)"
      - type: coalesce_field
        target: "target.notes"
    on_conflict:
      severity: error
      code: too_many_uncertainties_same_kind
      message: "Too many uncertainties of same type for a single sample."
```

The goal is not a full workflow engine. The goal is to capture the real grouped merge behavior that changes the persisted result.

### 4. Add First-Class Emitted Issues And Flags

Allow rules, resolvers, transforms, and postprocess actions to emit structured outcomes.

Add a shared `emit` shape:

```yaml
emit:
  severity: error|warning|ignored|flag
  code: <string>
  message: <string>
  set_flagged: true|false
```

This should be usable in:

- resolver steps
- reconciliation rules
- postprocess conflict handling
- optional transform or validation guards

This gives machine-readable shape to behavior that is currently buried in comments such as unknown uncertainty symbols, ignored rows, flagged fallback labs, and merge conflicts.

### 5. Add Known Divergences

Add an optional top-level `known_divergences` section so a policy can say when it intentionally follows Java runtime behavior, intentionally improves it, or is blocked by a known ambiguity.

Example:

```yaml
known_divergences:
  - area: update_detection
    status: java_bug_suspected
    description: "Java age update logic returns numeric equality instead of difference."
    policy_choice: "match_intended_behavior"
```

This is not a substitute for fixing Java bugs. It is a way to keep the policy honest when exact parity is uncertain.

## Alternatives Considered

### Keep Expanding Helper Comments

This is the cheapest short-term option, but it keeps critical behavior outside the executable part of the schema.

### Replace The Whole Schema With A Full DSL

This would likely overshoot the actual need. The current schema already handles simple mappings and ordered reconciliation well. The better move is to extend the existing structure at the proven pain points.

## Risks And Tradeoffs

- More schema structure means more authoring work per complex importer.
- A postprocess model can become too abstract if it is not kept tightly scoped to the already observed merge patterns.
- Resolver definitions will overlap somewhat with existing helper descriptions during migration.
- If divergences are recorded too casually, they can become a way to avoid hard decisions.

## Testing And Validation

Validation now happens in three layers, and the remaining work should keep using the same structure.

1. Schema validation: extend `_schema.yml` and `PolicyFormatValidationTest` so the new sections are checked structurally.
2. Example conversion: update a small set of existing policies to the new schema, starting with `datescalendar.policy.yml` and `datesradio.policy.yml`.
3. Behavioral fixtures: add small machine-readable fixtures for representative cases and compare the policy result with the current Java result.

The first fixture set now covers:

- calendar-date merge into a range row
- calendar-date merge conflict with too many same-kind uncertainties
- dating-lab resolution with blank lab ID
- dating-lab resolution with direct repository fallback
- dating-lab not-found error emission
- lab-country resolution with blank country error
- lab-country resolution with placeholder-country ignored outcome
- lab-country resolution with direct country lookup
- lab-country resolution with country-not-found error
- period-date method resolution with blank method fallback
- period-date method resolution with direct abbreviation lookup
- period-date method resolution with computed period-years-type suffix lookup
- period-date method not-found error emission
- fossil dataset clone plus analysis-entity link behavior when dataset updates are disabled
- fossil dataset reuse plus analysis-entity link behavior when dataset updates are enabled
- lab ordered reconciliation with trace-hit update, trace-hit error return, lab-id fallback update, and create-new branches
- bibliography ordered reconciliation with trace-hit update, trace-hit error return, database lookup update, and create-new branches
- country ordered reconciliation with trace-hit update, existing-country-name lookup update, and create-new branches
- site ordered reconciliation with prerequisite no-country guard return, trace-hit update, trace-hit error return, update-disallowed guard return, name-and-location single-match error, name-and-location multi-match error, and create-new branches
- sitereferences ordered reconciliation with prerequisite missing-site guard return, missing-reference guard return, missing-bibliography guard return, tuple-lookup update, and create-new branches
- ecocodegroup ordered reconciliation with trace-hit update and create-new branches
- ecocode_bugs ordered reconciliation with trace-hit update and create-new branches
- ecocode_koch ordered reconciliation with trace-hit update and create-new branches
- speciesassociation ordered reconciliation with trace-hit update, trace-hit error return, and create-new branches
- speciesbiology ordered reconciliation with tuple-lookup update and create-new branches
- specieskeys ordered reconciliation with tuple-lookup update and create-new branches
- speciessynonyms ordered reconciliation with trace-hit update and create-new branches
- ecocodedefinition_bugs ordered reconciliation with trace-hit update, trace-hit error return, and create-new branches
- ecocodedefinition_koch ordered reconciliation with trace-hit update, trace-hit error return, and create-new branches
- period ordered reconciliation with an ignored-item prerequisite return, trace-hit update, trace-hit error return, and create-new branches
- rdbsystem ordered reconciliation with trace-hit update, trace-hit error return, and create-new branches
- mcrnames ordered reconciliation with trace-hit update, species-value lookup update, and create-new branches
- taxaseasonality ordered reconciliation with trace-hit update, history-guard error return, repository lookup update, and create-new branches
- mcrsummary reconciliation with species lookup return-as-is and create-new branches
- birmbeetledata ordered reconciliation with composite-key lookup reuse and create-new branches
- species ordered reconciliation with code lookup reuse and create-new branches, plus supporting-output family, genus, author, species, the optional-author null branch, species create or reuse without author, and the no-data shortcut behavior, and a combined related-output graph for the full taxa tree
- sample supporting-output sample-dimensions create, update, keep-existing, and delete-existing branches
- datasetcontacts supporting-output contacts generated-new, repository-reuse, cache-reuse, identified-by-plus-specimen parse-order, and specimen-repository-only generated-new and repository-reuse branches
- calendar-date dataset supporting-output create, update, and keep-existing branches
- calendar-date analysis-entity supporting-output create, update, and keep-existing branches
- calendar-date grouped postprocess open-ended From, To, FromCa, and ToCa singleton retention branches
- geochronology analysis-entity supporting-output creation through the datesradio insert path
- fossil dataset supporting-output clone and reuse branches
- fossil analysis-entity supporting-output create and reuse branches
- datasetcontacts main-output list reconciliation for create-new rows, keep-existing rows, duplicate filtering, and append-only unmatched generated rows
- sitelocations main-output list reconciliation for create-new rows, keep-existing rows, mark-for-deletion rows, and replacement rows on the clean updater path, plus converter error-carrier returns for missing imported sites and location-manager error rows
- period-date dataset supporting-output create, update, and keep-existing branches
- period-date analysis-entity supporting-output create, update, and keep-existing branches
- period-date combined dataset plus analysis-entity graph create, update, keep-existing, blank-sample-code, missing-sample-trace, and unknown-uncertainty issue branches
- siteotherproxies main-output list reconciliation for create-new rows, keep-existing rows, mark-for-deletion rows, and append-new enabled proxy rows
- rdb ordered reconciliation with trace-hit update, history-conflict guard return, repository lookup update, and create-new branches
- rdbcode ordered reconciliation with trace-hit update, trace-hit error return, duplicate-value guard return, and create-new branches
- speciesdistribution ordered reconciliation with tuple-lookup update and create-new branches
- taxanotes ordered reconciliation with tuple-lookup update and create-new branches
- geochronology dataset supporting-output creation through the datesradio insert path
- geochronology dataset plus analysis-entity graph creation and missing-sample, missing-method, missing-date, and unknown-uncertainty error branches through datesradio
- calendar-date relative-age supporting-output creation and repository reuse through `RelativeAgeManager`
- calendar-date relative-age plus dataset plus analysis-entity graph creation through `RelativeDateUpdaterForCalendar`

Current limit:

- `PolicyFormatValidationTest` now validates that fixture files stay aligned with policy source fields, mapping targets, resolver steps, postprocess names, emit codes, related outputs, and known-divergence areas.
- `make validate-policy-format` now also runs a small executable comparison slice for `datescalendar` merge/conflict plus singleton-retention and multi-output partition behavior, `datescalendar` relative-age supporting and graph behavior, and `datesradio` dating-lab resolver paths.
- `make validate-policy-format` now also runs one fossil related-output manager check for the update-disabled cloned-dataset path.
- `make validate-policy-format` now also runs the update-enabled fossil dataset-reuse path so both sides of the current configuration fork are covered.
- Narrow policy harnesses now execute `datesradio` resolver paths, `datesperiod` resolver paths, and `lab` country-resolution paths, plus `country`, `site`, `sitereferences`, `ecocodegroup`, `ecocode_bugs`, `ecocode_koch`, `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, `period`, `rdbsystem`, `mcrnames`, `taxaseasonality`, `mcrsummary`, `birmbeetledata`, `species`, `lab`, `bibliography`, `rdb`, `rdbcode`, `speciesdistribution`, and `taxanotes` ordered reconciliation paths, `sample`, `datasetcontacts`, `datesperiod`, `datesradio`, `datescalendar`, `species`, and `fossil` supporting-output paths, `datescalendar` postprocess merge/conflict, singleton-retention, and multi-output partition paths, `datasetcontacts`, `siteotherproxies`, and `sitelocations` main-output list-result paths, and `fossil`, `datesperiod`, `datesradio`, `datescalendar`, and `species` related-output graph behavior from policy YAML.
- Fixture result comparisons now exist for resolver, ordered-reconciliation, postprocess, supporting-output, main-output list-result, and related-output graph slices across `datescalendar`, `datesradio`, `datesperiod`, `country`, `site`, `sitereferences`, `ecocodegroup`, `ecocode_bugs`, `ecocode_koch`, `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, `period`, `rdbsystem`, `mcrnames`, `taxaseasonality`, `mcrsummary`, `birmbeetledata`, `species`, `lab`, `bibliography`, `sample`, `datasetcontacts`, `siteotherproxies`, `sitelocations`, `rdb`, `rdbcode`, `speciesdistribution`, `taxanotes`, and `fossil`.
- The `datescalendar` Java fixture tests now compare the same `postprocess_result` and `postprocess_results` object shapes as the policy harness for paired merge, conflict, singleton-retention, and multi-output partition behavior and the same `graph_result` object shape as the policy harness for both the single `relative_age` supporting-output path and the broader related-output graph path.
- The `datesradio` Java fixture test now compares the same `resolver_result` object shape as the policy harness, so resolver checks now share one result-object format across Java and policy execution.
- The `datesperiod` Java fixture test now compares the same `resolver_result` object shape as the policy harness for blank fallback, direct lookup, computed suffix lookup, and the not-found error path.
- The `lab` Java fixture test now compares the same `resolver_result` object shape as the policy harness for blank country, placeholder-country ignored, direct lookup, and the not-found error path.
- The `lab` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, lab-id fallback update, and create-new ordered reconciliation paths.
- The `bibliography` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, case-insensitive database lookup update, and create-new ordered reconciliation paths.
- The `country` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, existing-country-name lookup update, and create-new ordered reconciliation paths.
- The `site` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for prerequisite no-country guard return, trace-hit update, trace-hit error return, update-disallowed guard return, name-and-location single-match error, name-and-location multi-match error, and create-new ordered reconciliation paths.
- The `sitereferences` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for prerequisite missing-site guard return, missing-reference guard return, missing-bibliography guard return, tuple-lookup update, and create-new ordered reconciliation paths.
- The `ecocodegroup` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update and create-new ordered reconciliation paths.
- The `ecocode_bugs` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update and create-new ordered reconciliation paths.
- The `ecocode_koch` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update and create-new ordered reconciliation paths.
- The `speciesassociation` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, and create-new ordered reconciliation paths.
- The `speciesbiology` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for tuple-lookup update and create-new ordered reconciliation paths.
- The `specieskeys` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for tuple-lookup update and create-new ordered reconciliation paths.
- The `speciessynonyms` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update and create-new ordered reconciliation paths.
- The `ecocodedefinition_bugs` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, and create-new ordered reconciliation paths.
- The `ecocodedefinition_koch` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, and create-new ordered reconciliation paths.
- The `period` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for the ignored-item prerequisite return, trace-hit update, trace-hit error return, and create-new ordered reconciliation paths.
- The `rdbsystem` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, and create-new ordered reconciliation paths.
- The `mcrnames` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace lookup, species-value lookup, and create-new ordered reconciliation paths.
- The `taxaseasonality` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace lookup, history-guard error return, repository lookup, and create-new ordered reconciliation paths.
- The `mcrsummary` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for species lookup return-as-is and create-new ordered reconciliation paths.
- The `birmbeetledata` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for composite-key lookup reuse and create-new ordered reconciliation paths.
- The `species` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for taxonomic-order code lookup reuse and create-new ordered reconciliation paths.
- The `sample` dimension-updater Java fixture test now compares the same `graph_result` object shape as the policy harness for `sample_dimensions` create, update, keep-existing, and delete-existing behavior.
- The `species` helper fixture test now compares the same `graph_result` object shape as the policy harness for family, genus, author, species, the optional-author null branch, species create or reuse without author, and the no-data shortcut supporting-output behavior.
- The `species` helper fixture test now also compares the same `graph_result` object shape as the related-output harness for full taxa-tree create and reuse graph paths.
- The `datasetcontacts` site-contact parser Java fixture test now compares the same `graph_result` object shape as the policy harness for supporting `contacts` generated-new, repository-reuse, cache-reuse, identified-by-plus-specimen parse-order, and specimen-repository-only generated-new and repository-reuse behavior.
- The `datasetcontacts` updater Java fixture test now compares the same `output_result` object shape as the policy harness for keep-existing rows, append-only unmatched generated rows, and no-generated keep-existing behavior in the main `tbl_dataset_contacts` output list.
- The `siteotherproxies` updater Java fixture test now compares the same `output_result` object shape as the policy harness for create-new rows, keep-existing rows, mark-for-deletion rows, and append-new enabled proxy rows in the main `tbl_site_other_records` output list.
- The `sitelocations` updater Java fixture test now compares the same `output_result` object shape as the policy harness for create-new rows, keep-existing rows, mark-for-deletion rows, and replacement rows in the main `tbl_site_locations` output list on the clean updater path.
- The `sitelocations` row-converter Java fixture test now compares the same `output_result` object shape as the policy harness for the missing-imported-site return and the location-manager error return branches before list reconciliation starts.
- The `rdb` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, history-conflict guard return, repository lookup update, and create-new ordered reconciliation paths.
- The `rdbcode` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for trace-hit update, trace-hit error return, duplicate-value guard return, and create-new ordered reconciliation paths. The current fixture contract also now allows `reconciliation_path` to flatten `search_chain` step names instead of only top-level rule names.
- The `speciesdistribution` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for tuple-lookup update and create-new ordered reconciliation paths.
- The `taxanotes` row-converter Java fixture test now compares the same `reconciliation_result` object shape as the policy harness for tuple-lookup update and create-new ordered reconciliation paths.
- The `datesperiod` dataset-updater Java fixture test now compares the same `graph_result` object shape as the policy harness for create-new, update-existing, and keep-existing dataset supporting-output paths.
- The `datesperiod` analysis-entity Java fixture test now compares the same `graph_result` object shape as the policy harness for create-new, update-existing, and keep-existing analysis-entity supporting-output paths.
- The `datesperiod` combined-graph Java fixture test now compares the same `graph_result` and `graph_issue` object shapes as the policy harness for create-new, update-existing, keep-existing, blank-sample-code, missing-sample-trace, and unknown-uncertainty related-output graph paths.
- The `datesradio` dataset-creator Java fixture test now compares the same `graph_result` object shape as the policy harness for the insert-path supporting-output dataset creation case.
- The `datesradio` analysis-entity-creator Java fixture test now compares the same `graph_result` and `graph_issue` object shapes as the policy harness for the dataset-plus-analysis-entity create path and the missing-sample error path.
- The `datesradio` updater Java fixture test now compares the same `graph_issue` object shape as the policy harness for missing-method, missing-date, and unknown-uncertainty error paths on the insert updater path.
- The `datescalendar` relative-age-manager Java fixture test now compares the same `graph_result` object shape as the policy harness for single calendar-date `relative_age` create and reuse supporting-output paths.
- The `datescalendar` updater Java fixture test now compares the same `graph_result` object shape as the policy harness for the `relative_age` plus `dataset` plus `analysis_entity` create graph path.
- The `datescalendar` updater Java fixture test now also compares the same `graph_result` object shape as the policy harness for isolated `dataset` create or update or keep and isolated `analysis_entity` create or update or keep supporting-output paths.
- The `datesradio` analysis-entity-creator Java fixture test now also compares the same `graph_result` object shape as the policy harness for the isolated `analysis_entity` supporting-output create path.
- The `fossil` analysis-entity-manager Java fixture test now also compares the same `graph_result` object shape as the policy harness for isolated `dataset` clone or reuse and isolated `analysis_entity` create or reuse supporting-output paths.
- The `fossil` related-output slice now covers a second concrete branch beyond the dataset-update fork: reusing an existing analysis entity from repository state.
- The `fossil` related-output slice now also covers a true failing branch: missing sample trace now returns a structured `graph_issue` result instead of only successful graph outputs.
- The `fossil` related-output slice now also covers the duplicate-analysis-entity error path, where the same sample and dataset resolve to more than one stored analysis entity and execution returns a structured `graph_issue` result.
- The `fossil` related-output slice now also covers the remaining `AnalysisEntityManager` guard branch for blank sample codes, including the current Java return value through `row_changed: true` alongside the structured `graph_issue` result.
- The fixture layer still does not execute policy logic generally. Current policy execution is still limited to a small number of hand-built resolver, postprocess, ordered-reconciliation, supporting-output, and related-output features, but those features now compare concrete returned result objects instead of only branch selection.

## Acceptance Criteria

- The schema can reference runnable related-output identities directly from parent mappings.
- The schema can express ordered resolver behavior without collapsing it into a free-text helper description.
- The schema can represent the `datescalendar` merge path without relying on prose alone.
- The schema can express structured emitted issues and flags.
- The schema can record machine-readable known divergences where exact Java parity is intentionally deferred or preserved.
- Representative policies use the new constructs and still pass format validation.
- Shared result-object comparisons exist across Java and policy execution for the first resolver, reconciliation, postprocess, supporting-output, and related-output graph slices.
- Fixture validation checks stay on the existing `make validate-policy-format` path.

## Completed Groundwork

1. Added `related_outputs[*].phase` plus `related.<name>.<field>` expression support.
2. Added first-class `resolvers` and converted helper-heavy lookup paths.
3. Added `postprocess` support for grouped merge behavior and converted the first `datescalendar` merge path.
4. Added shared `emit` blocks for issues and flags.
5. Added initial `known_divergences` support and the first concrete divergence example.
6. Added the first fixture-backed validation and shared-result comparisons across Java and policy execution.

## Recommended Delivery Order

1. Expand from the current hand-picked executable checks to broader fixture-driven Java comparisons.
2. Expand policy-side execution beyond the current hand-built importer slices toward broader fixture-driven policy result comparison. `site`, `sitereferences`, `period`, `rdbsystem`, `mcrnames`, `taxaseasonality`, `mcrsummary`, `birmbeetledata`, `species`, `speciessynonyms`, the ecocode definition slices, the ecocode slices, and the text-based tuple-lookup slices now show that the same shared result-object contract can cover prerequisite guards, trace-only reconciliation, ordered search chains, composite-key reuse, fixed supporting-output trees, full fixed related-output graphs, repository tuple reuse, and narrow return-as-is branches without widening the schema.
3. Continue expanding from full related-output graphs into smaller single-supporting-output controllers and updaters where that gives better branch isolation. The latest `datescalendar`, `datesradio`, `datesperiod`, `fossil`, `species`, and `datasetcontacts` follow-up slices now prove that the same shared harness can cover isolated child-output behavior, grouped postprocess singletons, grouped postprocess multi-output partitions, and updater error branches without reopening the broader graph path.
4. Expand from the current result-object comparisons to fuller fixture-driven policy result comparison without turning the schema into a general workflow DSL.

## Final Recommendation

Extend the current schema incrementally instead of replacing it.

The schema additions that this proposal argued for are now proving out in the repository, so the recommendation should stay narrow: keep the current model, extend it only where current importer behavior still disappears into helpers or comments, and keep validating it through shared result-object comparisons between Java and policy execution. The `datescalendar`, `datesradio`, `datesperiod`, `country`, `site`, `sitereferences`, `ecocodegroup`, `ecocode_bugs`, `ecocode_koch`, `speciesassociation`, `speciesbiology`, `specieskeys`, `speciessynonyms`, `ecocodedefinition_bugs`, `ecocodedefinition_koch`, `period`, `rdbsystem`, `mcrnames`, `taxaseasonality`, `mcrsummary`, `birmbeetledata`, `species`, `lab`, `bibliography`, `sample`, `datasetcontacts`, `siteotherproxies`, `sitelocations`, `rdb`, `rdbcode`, `speciesdistribution`, `taxanotes`, and `fossil` slices already show that this approach can cover resolvers, ordered reconciliation, grouped merge logic, supporting-output controllers, one-to-many main-output list reconciliation, prerequisite guards, trace-only reuse, ordered search chains, composite-key reuse, fixed supporting-output trees, tuple-based repository reuse, narrow return-as-is branches, trace-hit error returns, and related-output graphs without replacing the whole schema. The next step should be to improve how much policy behavior can execute through shared harnesses without introducing a general workflow DSL, not to chase another uncovered importer slice in this CR.
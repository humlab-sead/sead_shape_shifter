# Proposal: Generate Reconciliation Policies For All BugsCEP Importers

## Status

- Implemented inventory phase
- Scope: maintain the full reconciliation policy inventory for every importer in the `sead_bugs_import` Java application using `doc/reconciliation_policies/create-policy.instructions.md` as the default authoring path
- Goal: keep a complete, reviewable policy baseline for fidelity work, later code generation, and Shape Shifter comparison

## Summary

This proposal started the structured pass over all importer classes in the Java BugsCEP application and that inventory phase is now complete.

The work uses `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md` as the default authoring workflow, validates policy changes with the policy-format check, and tracks importer-by-importer coverage in one shared checklist.

The checklist in this document is now the completed inventory baseline. The active follow-up work is no longer broad policy generation. It is machine-readable fidelity work on the richer policy features captured in [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md).

## Problem

The Java importer still holds the authoritative BugsCEP business rules, but those rules are spread across many importer, mapper, updater, repository, helper, and trace classes.

That creates three immediate problems:

- rule extraction is slow and inconsistent without a standard workflow
- migration discussions stay abstract when only a few domains have policy files
- there is no single progress view that shows which importers already have reviewable policy coverage and which still depend on Java-only behavior

Without a full policy inventory, later migration work stays harder to compare, validate, and sequence.

## Scope

This proposal covers:

- generating one policy artifact for each importer class in `sead_bugs_import`
- using `create-policy.instructions.md` as the default extraction workflow
- validating generated policies with the existing format validator in `sead_bugs_import`
- keeping a single importer-level progress checklist in this proposal
- identifying importer classes that need an instruction extension or a special policy pattern

## Non-Goals

This proposal does not attempt to:

- generate Python importer code in this phase
- replace the Java importer directly
- prove full runtime parity between policy files and Java behavior
- turn every completed policy into a fully executable policy model in one pass
- resolve every complex importer edge case before simpler importers are captured

## Current Behavior

The current policy authoring path exists in `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md` and is backed by a policy schema plus a validator command: `make validate-policy-format` in `sead_bugs_import`.

The importer inventory phase is complete. Every importer class in `sead_bugs_import/src/main/java/se/sead/bugsimport/` now appears in the checklist below, with a mapped policy artifact or an explicit single-table review outcome where appropriate.

The policy set now includes both simple single-table domains and richer policies that use runnable `related_outputs`, `resolvers`, `postprocess`, shared `emit` outcomes, fixture-backed scenarios, and narrow Java-versus-policy comparisons.

The Java application currently exposes 35 importer classes under `sead_bugs_import/src/main/java/se/sead/bugsimport/`.

Not all importers fit the standard authoring path equally well. That is now reflected in the inventory: some policies remain intentionally single-table, while others carry richer supporting-row, child-row, or grouped postprocess behavior.

## Proposed Design

### Default Workflow

Use `create-policy.instructions.md` as the default path for every importer unless the importer clearly falls outside the supported pattern.

For each importer:

1. Gather the Java source evidence described by the instructions.
2. Draft the policy YAML in `sead_bugs_import/doc/reconciliation_policies/`.
3. Record non-obvious business-rule decisions in the matching decisions log.
4. Run `make validate-policy-format`.
5. Update the progress checklist in this proposal.

### Progress Tracking

Track progress at the importer-class level, not only at the policy-file level.

This keeps the checklist aligned with the Java system boundary the migration must eventually replace.

Where one importer is expected to need more than one policy artifact or a custom pattern, keep one importer checkbox here and explain the special handling inline.

### Delivery Order

Use dependency-aware ordering.

Start with leaf or low-dependency importers, then move to importer chains that reuse those policies as reference material. Keep special-case importers visible, but do not let them block steady progress on standard domains.

### Exception Handling

If an importer cannot be represented with the current instructions:

- do not force it into the standard pattern
- document why it fails the standard path
- either extend the instructions/schema deliberately or create a separate policy pattern for that importer class

## Risks And Tradeoffs

- A full importer inventory is useful, but it will expose many places where the Java behavior is more conditional than the current policy schema.
- Some importers will need richer prerequisite, helper, or custom-reader treatment than the simplest examples.
- Progress tracking by importer is clearer for planning, but it can hide the fact that some importers may need multiple sub-policies or follow-up refinements.
- If policy authoring starts without disciplined validation, the checklist can give false confidence.

## Testing And Validation

Each completed policy should be validated in `sead_bugs_import` with:

```bash
cd /home/roger/source/sead_bugs_import
make validate-policy-format
```

Validation expectations:

- the policy file matches `_schema.yml`
- the policy passes `PolicyFormatValidationTest`
- a matching decisions log exists for non-obvious behavior
- the importer checklist in this proposal is updated in the same change

## Acceptance Criteria

- Every importer class in `sead_bugs_import` appears in the progress checklist.
- Every importer that fits the standard pattern has a policy file generated from the current instructions.
- Every importer that does not fit the standard pattern is explicitly marked with the reason and the required follow-up.
- The completed policies pass `make validate-policy-format`.
- The checklist shows current progress without requiring a separate inventory document.

These criteria are now met for the inventory phase.

## Recommended Delivery Order

### Tier 1: Already Completed

- [x] `BibliographyImporter` -> `bibliography.policy.yml`
- [x] `SiteImporter` -> `site.policy.yml`
- [x] `LabImporter` -> `lab.policy.yml`

### Tier 2: Leaf Importers With Standard Path

- [x] `CountryImporter` -> `country.policy.yml`
- [x] `PeriodImporter` -> `period.policy.yml`
- [x] `RdbSystemImporter` -> `rdbsystem.policy.yml`
- [x] `EcocodeGroupImporter` -> `ecocodegroup.policy.yml`
- [x] `McrNamesImporter` -> `mcrnames.policy.yml`
- [x] `SpeciesAssociationImporter` -> `speciesassociation.policy.yml`
- [x] `SpeciesDistributionImporter` -> `speciesdistribution.policy.yml`
- [x] `TextBiologyImporter` -> `speciesbiology.policy.yml`
- [x] `IdentificationKeysImporter` -> `specieskeys.policy.yml`
- [x] `SynonymImporter` -> `speciessynonyms.policy.yml`
- [x] `TaxonomicNotesImporter` -> `taxanotes.policy.yml`
- [x] `TaxaSeasonalityImporter` -> `taxaseasonality.policy.yml`

### Tier 3: Importers With 1-2 Standard Dependencies

- [x] `RdbCodeImporter` -> `rdbcode.policy.yml`
- [x] `RdbImporter` -> `rdb.policy.yml`
- [x] `BugsDefinitionImporter` -> `ecocodedefinition_bugs.policy.yml`
- [x] `KochDefinitionImporter` -> `ecocodedefinition_koch.policy.yml`
- [x] `BugsEcocodeImporter` -> `ecocode_bugs.policy.yml`
- [x] `KochEcocodesImporter` -> `ecocode_koch.policy.yml`
- [x] `MCRSummaryImporter` -> `mcrsummary.policy.yml`
- [x] `BirmBeetleDataImporter` -> `birmbeetledata.policy.yml`
- [x] `SiteReferencesImporter` -> `sitereferences.policy.yml`
- [x] `SiteLocationImporter` -> `sitelocations.policy.yml`
- [x] `SiteOtherProxiesImporter` -> `siteotherproxies.policy.yml`

Tier 3 note: `sitelocations.policy.yml` and `siteotherproxies.policy.yml` now use the first-class `output` schema for one-to-many row expansion and deletion-marking.

### Tier 4: Higher-Dependency Or Richer Logic Importers

- [x] `IndexImporter` -> `species.policy.yml`
- [x] `SampleGroupImporter` -> `samplegroup.policy.yml`
- [x] `SampleImporter` -> `sample.policy.yml`
- [x] `FossilImporter` -> `fossil.policy.yml`
- [x] `DatasetContactImporter` -> `datasetcontacts.policy.yml`
- [x] `DatesCalendarImporter` -> `datescalendar.policy.yml`
- [x] `DatesPeriodImporter` -> `datesperiod.policy.yml`
- [x] `GeochronologyImporter` -> `datesradio.policy.yml`
- [x] `TaxaMeasuredAttributesImporter` -> `attributes.policy.yml`

Tier 4 status:

- Runnable `related_outputs`: `sample.policy.yml`, `species.policy.yml`, `fossil.policy.yml`, `datasetcontacts.policy.yml`, `datescalendar.policy.yml`, and `datesperiod.policy.yml`
- Reviewed and intentionally single-table: `samplegroup.policy.yml` and `attributes.policy.yml`
- Runnable `related_outputs` with insert-only child graph: `datesradio.policy.yml`

Tier 4 review result: all Tier 4 importers have now been checked against the current runnable-completeness goal. The remaining difference inside this tier is not coverage, but importer shape: some policies now model runnable child/supporting rows, while `samplegroup.policy.yml` and `attributes.policy.yml` remain single-table by design because their extra dependencies are resolved lookups only.

## Next Phase Direction

The machine-runnable completeness phase is now underway.

The schema and validator now support runnable `related_outputs`, and the current converted examples cover several distinct patterns:

- generated child rows under one parent row in `sample.policy.yml`
- cached or repository-matched supporting rows in `species.policy.yml`, `fossil.policy.yml`, and `datasetcontacts.policy.yml`
- cascaded supporting rows under shared relative-date updaters in `datescalendar.policy.yml` and `datesperiod.policy.yml`
- insert-only supporting rows in `datesradio.policy.yml`
- single-table reviewed cases with lookup-only dependencies in `samplegroup.policy.yml` and `attributes.policy.yml`

The next follow-up work should keep extending coverage importer by importer while explicitly marking the cases that stay single-table, so the tracker distinguishes real missing runnable child behavior from importers that only resolve lookup dependencies.

The proposed schema-extension path for that follow-up work is captured in [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md).

## Final Recommendation

Treat this proposal as the completed importer-inventory baseline.

Keep using `create-policy.instructions.md` as the default workflow, validate policy changes with `make validate-policy-format`, and use the checklist in this proposal when fidelity work changes how an importer is represented.

For active follow-up work, use [BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md](BUGSCEP_POLICY_SCHEMA_MACHINE_READABLE_FIDELITY.md). That document now captures the current schema-extension and fixture-comparison path beyond the completed inventory phase.
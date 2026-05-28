# Proposal: Generate Reconciliation Policies For All BugsCEP Importers

## Status

- Proposed change request
- Scope: generate and track reconciliation policy files for every importer in the `sead_bugs_import` Java application using `doc/reconciliation_policies/create-policy.instructions.md` as the default authoring path
- Goal: produce a complete policy inventory that captures importer business rules in YAML and creates a reviewable migration baseline for later code generation and Shape Shifter comparison

## Summary

This proposal recommends a structured pass over all importer classes in the Java BugsCEP application to extract their business rules into reconciliation policy YAML files.

The work should use `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md` as the default authoring workflow, validate each generated policy with the policy-format check, and track completion importer by importer in one shared checklist.

This is the right time to do it because the instruction file, schema, examples, and validator now exist and are aligned well enough to support repeatable policy authoring.

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
- redesign the policy schema again before policy generation starts
- resolve every complex importer edge case before simpler importers are captured

## Current Behavior

The current policy authoring path now exists in `sead_bugs_import/doc/reconciliation_policies/create-policy.instructions.md` and is backed by a policy schema plus a validator command: `make validate-policy-format` in `sead_bugs_import`.

Three policy files already exist and validate:

- `bibliography.policy.yml`
- `site.policy.yml`
- `lab.policy.yml`

The Java application currently exposes 35 importer classes under `sead_bugs_import/src/main/java/se/sead/bugsimport/`.

Not all importers fit the standard authoring path equally well. Some use custom parsing, internal location side effects, or complex sub-domain behavior that may need an instruction extension or a companion policy shape.

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

## Recommended Delivery Order

### Tier 1: Already Completed

- [x] `BibliographyImporter` -> `bibliography.policy.yml`
- [x] `SiteImporter` -> `site.policy.yml`
- [x] `LabImporter` -> `lab.policy.yml`

### Tier 2: Leaf Importers With Standard Path

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

- [ ] `RdbCodeImporter` -> `rdbcode.policy.yml`
- [ ] `RdbImporter` -> `rdb.policy.yml`
- [ ] `BugsDefinitionImporter` -> `ecocodedefinition_bugs.policy.yml`
- [ ] `KochDefinitionImporter` -> `ecocodedefinition_koch.policy.yml`
- [ ] `BugsEcocodeImporter` -> `ecocode_bugs.policy.yml`
- [ ] `KochEcocodesImporter` -> `ecocode_koch.policy.yml`
- [ ] `MCRSummaryImporter` -> `mcrsummary.policy.yml`
- [ ] `BirmBeetleDataImporter` -> `birmbeetledata.policy.yml`
- [ ] `SiteReferencesImporter` -> `sitereferences.policy.yml`
- [ ] `SiteLocationImporter` -> `sitelocations.policy.yml`
- [ ] `SiteOtherProxiesImporter` -> `siteotherproxies.policy.yml`

### Tier 4: Higher-Dependency Or Richer Logic Importers

- [ ] `IndexImporter` -> `species.policy.yml` (complex importer; likely needs extra rule detail)
- [ ] `SampleGroupImporter` -> `samplegroup.policy.yml`
- [ ] `SampleImporter` -> `sample.policy.yml`
- [ ] `FossilImporter` -> `fossil.policy.yml`
- [ ] `DatesCalendarImporter` -> `datescalendar.policy.yml`
- [ ] `DatesPeriodImporter` -> `datesperiod.policy.yml`
- [ ] `GeochronologyImporter` -> `datesradio.policy.yml`
- [ ] `TaxaMeasuredAttributesImporter` -> `attributes.policy.yml`

### Tier 5: Importers That Need Instruction Extension Or Custom Policy Pattern

- [ ] `CountryImporter` -> special handling required; current inventory treats locations as an internal side effect rather than a standard importer domain
- [ ] `DatasetContactImporter` -> special handling required; current implementation reads and parses site contact strings rather than following the normal `BugsTable` pattern

## Open Questions

- Should `SampleGroupImporter` be tracked as one importer-level policy only, or should its secondary countsheet-facing output be tracked as a second explicit artifact in a later phase?
- Should `CountryImporter` be modeled as a standard policy, or kept as an internal support domain with a smaller custom format?
- Should `IndexImporter` stay in the standard queue, or be broken into a separate high-risk work item because of taxonomic complexity?

## Final Recommendation

Start a full importer-by-importer reconciliation policy pass now.

Use `create-policy.instructions.md` as the default workflow, validate every completed policy with `make validate-policy-format`, and use the checklist in this proposal as the authoritative progress tracker for policy coverage across the Java importer.
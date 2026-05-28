# Proposal: BUGSCEP Pilot Project In Shape Shifter

## Status

- Current state: pilot draft implemented and validated on the current branch
- Scope: document the current BugsCEP Shape Shifter pilot, the decisions already made, and the next implementation slices
- Goal: use a real, validated BugsCEP pilot project as the baseline for continued migration work from the Java importer toward Shape Shifter

## Summary

This proposal recommends treating the current BugsCEP Shape Shifter draft as an explicit pilot project rather than as a loose experiment.

The pilot already covers a meaningful SEAD-facing slice and has been validated against a real BugsCEP `.mdb` file. It now includes site, location, bibliography, dating-lab, relative-age, sample, dataset, analysis-entity, relative-dating, and geochronology scaffolding in [data/projects/bugs/shapeshifter.yml](../../data/projects/bugs/shapeshifter.yml).

The right next step is not a rewrite. It is to keep extending this pilot in small importer-aligned slices, preserve important Java-only behavior in comments where Shape Shifter does not yet express it directly, and use repeatable validation against the real BugsCEP file after each slice.

## Problem

The current Java BugsCEP importer contains the working mapping logic, but it is harder to review, extend, and separate into small decision points.

Before this pilot work, there was no validated Shape Shifter project for BugsCEP that showed:

- which SEAD-facing entities can already be shaped directly from the Access source
- which Java behaviors map cleanly into YAML
- which behaviors still need comments, explicit project policy, or future Shape Shifter features
- how far a practical migration can move without claiming full importer parity too early

Without a concrete pilot, migration discussion stays abstract.

## Scope

This proposal covers:

- the current pilot baseline in [data/projects/bugs/shapeshifter.yml](../../data/projects/bugs/shapeshifter.yml)
- the design decisions made while building that baseline
- the work completed so far
- the next recommended delivery order for future work

## Non-Goals

This proposal does not attempt to:

- claim full feature parity with the Java importer
- replace the Java importer immediately
- model every remaining BugsCEP importer in one pass
- resolve every current review warning before continuing pilot work
- define the final production deployment plan for a BugsCEP Shape Shifter workflow

## Current Behavior

The pilot project lives in [data/projects/bugs/shapeshifter.yml](../../data/projects/bugs/shapeshifter.yml) and the mirrored test-data copy lives in [tests/test_data/projects/bugs/shapeshifter.yml](../../tests/test_data/projects/bugs/shapeshifter.yml).

The current pilot uses UCanAccess against a real BugsCEP `.mdb` file through `BUGS_CEP_MDB_FILE` and validates with:

```bash
cd /home/roger/source/sead_shape_shifter
BUGS_CEP_MDB_FILE=../sead_bugs_import/bugsdata/bugsdata_20231219.mdb \
./.venv/bin/python scripts/validate_project.py data/projects/bugs/shapeshifter.yml
```

The pilot currently includes these main SEAD-facing slices:

- site and location context
- bibliography and site references
- dating laboratories
- relative-age classifiers and relative ages
- sample, sample-group, dataset, and analysis-entity backbone
- dating uncertainty
- relative dating
- geochronology

The current accepted review warnings are:

- one unmatched `dating_uncertainty`
- two unmatched `dating_lab` values: `Suerc` and `Birmingham`

## Proposed Design

### Pilot Baseline

Treat the current YAML project as the official pilot baseline for BugsCEP migration work.

That means:

- keep building from the current project file instead of restarting from a cleaner but less-tested draft
- preserve importer-aligned behavior where it is already understood
- document Java-only behavior in comments when Shape Shifter does not yet express it directly
- keep validation against the real `.mdb` file as the main acceptance check for each slice

### Current Design Decisions

The pilot already depends on several explicit decisions.

- `bugs_site_code` stays the primary business key for the site slice
- staging columns such as `country_name`, `region_name`, and other Bugs-side identifiers are kept when they help link SEAD-facing rows
- placeholder public-id columns are included in SQL entities where current Shape Shifter linking and validation expect them
- optional lookups that should not delete fact rows use `how: left`
- UCanAccess union literals are normalized with `trim(...)` so padded strings do not break joins
- blank `TDatesPeriod.DatingMethod` uses `UnknownCal`, matching the Java relative-date fallback
- blank `TDatesRadio.DatingMethod` now uses explicit project policy `UnknownRadio`, so the row stays visible instead of being dropped during dataset-method linking

### Migration Strategy

Continue with small, importer-aligned slices.

Each slice should:

- start from one concrete importer or one tight set of related entities
- model the extract-and-shape path first
- keep unresolved reconciliation or update logic in comments instead of inventing false executable behavior
- validate against the real BugsCEP file before moving on

This keeps the pilot honest.

## Completed Work Checklist

- [x] Create the initial BugsCEP project file in [data/projects/bugs/shapeshifter.yml](../../data/projects/bugs/shapeshifter.yml)
- [x] Configure UCanAccess source access with `BUGS_CEP_MDB_FILE` and `lib/ucanaccess`
- [x] Add the first `site` entity sourced from `TSite`
- [x] Keep `bugs_site_code` as the main business key for the site slice
- [x] Add `location_type` fixed rows for `Country` and `Sub-country administrative region`
- [x] Add `location` and `site_location` to represent the SEAD-facing location output from Bugs site data
- [x] Add `citation` from `TBiblio`
- [x] Add `site_reference` from `TSiteRef`
- [x] Add `dating_lab` from `TLab` while intentionally leaving `country_id` as future work
- [x] Add `relative_age_type` and `relative_ages` from `TPeriods`
- [x] Add the first dating backbone with `sample_type`, `alt_ref_type`, `method_group`, `method`, `data_type`, `sample_group`, `sample`, `dataset`, and `analysis_entity`
- [x] Add `dating_uncertainty`
- [x] Add `relative_dating` from `TDatesPeriod`
- [x] Add `geochronology` from `TDatesRadio`
- [x] Replace provisional dating methods and data types with importer-aligned method abbreviations and Java-aligned data-type names
- [x] Add the Java-style `UnknownCal` fallback for blank relative-date methods
- [x] Add the explicit Shape Shifter `UnknownRadio` policy for blank geochronology methods
- [x] Mirror the project into [tests/test_data/projects/bugs/shapeshifter.yml](../../tests/test_data/projects/bugs/shapeshifter.yml)
- [x] Validate the pilot repeatedly against `bugsdata_20231219.mdb`
- [x] Reduce current validation output to accepted review warnings rather than workflow errors
- [x] Record important implementation notes, including the UCanAccess padded-literal quirk, in repository memory

## Risks And Tradeoffs

The pilot is useful now, but it still carries deliberate tradeoffs.

- It does not yet replicate the full Java trace, update, and external-edit protection logic as executable Shape Shifter behavior.
- Some project behavior is currently documented in comments rather than modeled in first-class configuration constructs.
- The explicit `UnknownRadio` rule is a project policy, not a copied Java behavior.
- Remaining unmatched-lab and unmatched-uncertainty warnings still need review, even if they are acceptable for the pilot.
- The current dataset and analysis-entity backbone is enough for dating work, but not yet a full representation of all Bugs sample behavior.

These tradeoffs are acceptable for a pilot as long as they remain visible and deliberate.

## Testing And Validation

Each future slice should be validated in the same way as the current pilot.

- Run `scripts/validate_project.py` against the real BugsCEP `.mdb` file.
- Treat workflow errors as blockers.
- Treat known unmatched-lab and unmatched-uncertainty issues as review warnings unless policy changes.
- Keep the mirrored test-data YAML copy in sync with the main pilot file.
- When a new slice introduces row loss, inspect whether the loss is expected policy, missing method coverage, padded-literal behavior, or an incorrect join.

## Acceptance Criteria

The pilot should be considered a stable baseline when these conditions hold.

- [x] The project validates successfully against the real BugsCEP `.mdb` file.
- [x] The site, bibliography, relative-age, sample, and dating backbone slices are present in executable YAML.
- [x] The project documents important non-modeled Java behavior inline where needed.
- [x] The remaining validation issues are limited to accepted review warnings rather than workflow failures.
- [x] The pilot provides a credible base for incremental follow-up work.

## Recommended Delivery Order

### Near-Term Checklist

- [ ] Review the remaining unmatched `dating_uncertainty` value and decide whether it should stay a warning, map to an existing classifier, or become a new fixed row
- [ ] Review `Suerc` and `Birmingham` in `dating_lab` and decide whether they should be normalized, mapped, or remain review warnings
- [ ] Add a proper `country_id` strategy for `dating_lab` without misusing `location_id`
- [ ] Model `MaterialType` from `TDatesRadio` into a SEAD-facing dating-material slice if the target-model path is ready
- [ ] Move more Java-only dating behavior from comments into executable configuration where Shape Shifter now supports it

### Backbone Follow-Up Checklist

- [ ] Expand the sample slice to cover dimensions, depth, coordinates, and alternative references more faithfully
- [ ] Decide whether countsheet-specific logic should remain a thin bridge or become a richer sample-group slice
- [ ] Model additional sample and sample-group metadata that the Java importer currently carries outside the pilot
- [ ] Revisit whether `site_reference` should stay as a pilot-only table mapping or should wait for fuller target-model support

### Broader Pilot Expansion Checklist

- [ ] Continue importer-by-importer expansion from the current baseline instead of opening many unrelated slices at once
- [ ] Prioritize next slices that produce clear SEAD-facing entities with real Bugs source data and limited policy ambiguity
- [ ] Add project-level notes for every explicit policy that differs from current Java behavior
- [ ] Add narrow validation or regression tests around the Bugs pilot where the current tooling makes that practical
- [ ] Define the point at which the pilot is strong enough for a more formal migration comparison with the Java importer

## Open Questions

- Should the accepted review warnings stay accepted for the full pilot phase, or should any of them become blockers before broader expansion?
- Which remaining Java-only reconciliation behaviors are important enough to justify new Shape Shifter features rather than more YAML comments?
- At what point should the pilot stop expanding breadth-first and instead focus on parity for one end-to-end importer path?

## Final Recommendation

Keep the current BugsCEP Shape Shifter draft as the official pilot project.

Do not restart it. Do not broaden it all at once. Continue from the validated baseline in small importer-aligned slices, preserve explicit project policies where the YAML now makes them possible, and keep using real-file validation after each change.
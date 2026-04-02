# Proposal: Complete SEAD v2 Target Model Specification

## Context

The `sead_v2.yml` target model specification covers ~36 entities. An extended model `sead_standard_model.yml` has been created that adds Phase 1-4 entities (spatial, sample-metadata, dating, taxonomy, ecology, and analysis), bringing coverage to 70 entities. The actual SEAD Clearinghouse database contains 100+ tables. Analysis of the Arbodat Shape Shifter project reveals significant remaining gaps in entity coverage that prevent effective conformance validation.

## Problem Statement

**Missing Coverage:** Many entities used in real-world SEAD data transformation projects (e.g., Arbodat) are not specified in the target model, resulting in:
- Inability to validate conformance for complete projects
- No formal specification for spatial coordinates, dating details, site properties, sample dimensions, or taxon metadata
- Inconsistent entity naming and relationship documentation

**Coverage in `sead_v2.yml` (36 entities):**
Core: location, location_type, site, site_location, sample_group, sample, analysis_entity, dataset, method, project, citation, contact

Abundance: abundance, abundance_element, abundance_element_group, abundance_modification, abundance_property

Dating: relative_ages, relative_dating, geochronology, dating_lab

Taxonomy: taxa_tree_master, taxa_common_names

Classifiers: sample_type, sample_description_type, site_type, site_type_group, contact_type, method_group, modification_type, feature_type, feature

Bridges: dataset_contact, sample_feature

**Coverage in `sead_standard_model.yml` (70 entities — adds 34):**

*Phase 1 additions (13):* dimension, coordinate_method_dimension, sample_coordinate, alt_ref_type, sample_alt_ref, sample_dimension, identification_level, abundance_ident_level, age_type, relative_age_type, chronology, dating_uncertainty, dating_material

*Phase 2 additions (9):* sample_group_description_type, sample_group_description, sampling_context, lithology, site_preservation_status, site_other_record, dataset_method, dataset_submission_type, dataset_submission

*Phase 3 additions (7):* ecocode_system, ecocode_group, ecocode_definition, ecocode, activity_type, season_type, season

*Phase 4 additions (5):* record_type, unit, data_type_group, data_type, measured_value

**Total in `sead_standard_model.yml`: 70 entities (all fully specified)**

**Arbodat Project Uses (54 entities):**
Includes all above PLUS: coordinate_system, coordinate_method_dimension, dimension, sample_coordinate, dating (general), dating_period, archaeological_period, chronological_period, epoch, cultural_group, feature_property, feature_property_type, site_property, site_property_type, site_natural_region, natural_region, natural_region_group, dataset_submission, dataset_submission_type, abundance_property_type, identification_level, taxa (general taxon), taxa_use_categories, taxa_plant_sociological_behaviour

## Gap Analysis by Domain

### 1. Spatial/Coordinate Domain (High Priority)
**Addressed in `sead_standard_model.yml`:** dimension ✅, coordinate_method_dimension ✅, sample_coordinate ✅

**Still missing:** coordinate_system, sample_group_coordinate, site_natgridref

**Impact:** Cannot validate spatial metadata for samples or sample groups

**SEAD Tables:**
- `tbl_coordinate_method_dimensions` - coordinate measurement methods with dimensional constraints
- `tbl_dimensions` - measurement dimensions (X, Y, Z, depth, altitude, etc.)
- `tbl_sample_coordinates` - coordinates attached to physical samples
- `tbl_sample_group_coordinates` - coordinates attached to sample groups
- `tbl_site_natgridrefs` - national grid references for sites

### 2. Dating Domain (Medium Priority)
**Fully specified in `sead_standard_model.yml`:** dating_material ✅, dating_uncertainty ✅, chronology ✅, age_type ✅, relative_age_type ✅

**Still missing:** dating_period (analysis_entity → archaeological/chronological period)

**Impact:** Cannot validate complete dating workflows or period assignments

**SEAD Tables:**
- `tbl_dating_material` - material dated (links to abundance_element)
- `tbl_dating_uncertainty` - uncertainty qualifiers for dates
- `tbl_chronologies` - chronological frameworks
- `tbl_age_types` - age notation systems (AD, BC, BP, cal BP)
- Analysis entity links to relative_age via `tbl_relative_dates`

### 3. Feature Domain (Medium Priority)
**Missing:** feature_property, feature_property_type, sample_feature (exists but minimal)

**Impact:** Cannot validate feature metadata or sample-feature relationships

**SEAD Tables:**
- `tbl_physical_sample_features` - bridge between samples and features
- Feature properties would use `tbl_sample_description_types` pattern

### 4. Site Domain (Medium Priority)
**Addressed in `sead_standard_model.yml`:** site_preservation_status ✅, site_other_record ✅

**Still missing:** site_property, site_property_type, site_natural_region, natural_region, natural_region_group, site_reference

**Impact:** Cannot validate rich site metadata present in archaeological projects

**SEAD Tables:**
- `tbl_site_other_records` - additional site documentation/references
- Natural region data appears custom to Arbodat (German geographic classification)
- Site properties would follow description pattern

### 5. Sample Domain (High Priority)
**Addressed in `sead_standard_model.yml`:** sample_dimension ✅, sample_alt_ref ✅, alt_ref_type ✅

**Still missing:** sample_horizon, sample_location, sample_location_type, sample_note, sample_colour, colour

**Impact:** Cannot validate sample physical characteristics and alternate identifiers

**SEAD Tables:**
- `tbl_sample_dimensions` - physical dimensions of samples
- `tbl_sample_horizons` - horizon associations
- `tbl_sample_locations` - location metadata
- `tbl_sample_alt_refs` - alternative references (lab numbers, field IDs)
- `tbl_alt_ref_types` - classifier for alt reference types
- `tbl_sample_notes` - free-text notes
- `tbl_sample_colours` - Munsell/colour classifications

### 6. Sample Group Domain (Medium Priority)
**Addressed in `sead_standard_model.yml`:** sample_group_description_type ✅, sample_group_description ✅, sampling_context ✅, lithology ✅

**Still missing:** sample_group_dimension, sample_group_note, sample_group_reference

**Impact:** Cannot validate sample group metadata and context

**SEAD Tables:**
- `tbl_sample_group_descriptions` - typed descriptions
- `tbl_sample_group_description_types` - description classifiers
- `tbl_sample_group_dimensions` - physical dimensions
- `tbl_sample_group_notes` - free-text notes
- `tbl_sample_group_references` - bibliography links
- `tbl_sample_group_sampling_contexts` - sampling context classifier
- `tbl_lithology` - lithological descriptions linked to sample groups

### 7. Dataset Domain (Low Priority)
**Fully addressed in `sead_standard_model.yml`:** dataset_method ✅, dataset_submission ✅, dataset_submission_type ✅

**Impact:** Cannot validate multi-method datasets or submission workflow

**SEAD Tables:**
- `tbl_dataset_methods` - multiple methods per dataset
- `tbl_dataset_submissions` - submission tracking
- `tbl_dataset_submission_types` - submission type classifier

### 8. Taxon Domain (Medium Priority)
**Addressed in `sead_standard_model.yml`:** ecocode_system ✅, ecocode_group ✅, ecocode_definition ✅, ecocode ✅, activity_type ✅, season_type ✅, season ✅

**Still missing:** taxon_synonyms, rdb (red data book), taxon_measured_attributes

**Impact:** Cannot validate taxon metadata, ecological classifications, or conservation status

**SEAD Tables:**
- `tbl_taxa_tree_master` (exists) - taxonomic hierarchy backbone
- `tbl_taxa_synonyms` - synonym relationships
- `tbl_ecocodes` - ecological indicator codes per taxon
- `tbl_ecocode_definitions` - ecocode value definitions
- `tbl_ecocode_groups` - ecocode category grouping
- `tbl_ecocode_systems` - ecocode classification systems
- `tbl_rdb` - red data book conservation status
- `tbl_activity_types` - phenological/activity states
- `tbl_seasons` - seasonal classifications

### 9. Abundance Domain (Low Priority)
**Fully specified in `sead_standard_model.yml`:** identification_level ✅, abundance_ident_level ✅

**Still missing:** abundance_property_type

**Impact:** Cannot validate identification confidence or typed abundance properties

**SEAD Tables:**
- `tbl_abundance_ident_levels` - confidence in taxonomic ID (cf. Family, cf. Species)
- `tbl_identification_levels` - classifier for ID levels
- Abundance property types would follow standard pattern

### 10. Analysis Value Domain (Low Priority)
**Missing:** analysis_value (generic), analysis_categorical_value, analysis_boolean_value, analysis_integer_value, analysis_numerical_value, analysis_date_range, measured_value, analysis_note, analysis_identifier

**Impact:** Cannot validate non-abundance analytical observations (chemistry, isotopes, dimensions)

**SEAD Tables:**
- `tbl_analysis_values` - generic analysis value parent
- `tbl_analysis_categorical_values` - categorical results
- `tbl_analysis_boolean_values` - true/false results
- `tbl_analysis_integer_values` - integer measurements
- `tbl_analysis_numerical_values` - decimal measurements
- `tbl_analysis_dating_ranges` - date range values
- `tbl_measured_values` - direct measurements
- `tbl_analysis_notes` - free-text analytical notes
- `tbl_analysis_identifiers` - analytical identifiers

### 11. Project Domain (Low Priority)
**Missing:** project_type, project_stage

**Impact:** Cannot validate project classification and workflow stage

**SEAD Tables:**
- `tbl_project_types` - project classification
- `tbl_project_stages` - project workflow stages

### 12. Method Domain (Low Priority)
**Fully addressed in `sead_standard_model.yml`:** record_type ✅, unit ✅, data_type_group ✅, data_type ✅

**Impact:** Cannot validate method classification and result typing

**SEAD Tables:**
- `tbl_record_types` - type of record produced by method
- `tbl_units` - measurement units
- `tbl_data_types` - data type produced by method
- `tbl_data_type_groups` - data type grouping

## Reference Implementation

**Authoritative Source:** `resources/target_models/sead_standard_model.yml`

This file contains the complete and current SEAD v2 target model specification developed through Arbodat requirements analysis. All entity definitions, foreign keys, column specifications, and domain classifications are maintained in this YAML file to avoid duplication and synchronization issues.

For entity specifications, constraints, and relationship details, refer directly to `sead_standard_model.yml`.

## Implementation Plan

### Phase 1: Core Enhancements (Immediately needed for Arbodat)
- [x] Add spatial/coordinate entities (dimension, coordinate_method_dimension, sample_coordinate) — fully specified in `sead_standard_model.yml`
- [x] Add sample metadata entities (alt_ref_type, sample_alt_ref, sample_dimension) — fully specified in `sead_standard_model.yml`
- [x] Add abundance precision entities (identification_level, abundance_ident_level) — fully specified in `sead_standard_model.yml`
- [x] Add dating metadata entities (dating_material, dating_uncertainty, age_type, relative_age_type, chronology) — fully specified in `sead_standard_model.yml`
- [x] All Phase 1 entities fully specified in `sead_standard_model.yml` — 13 additions complete
- [x] Update key existing entity specs (sample now includes sample_type_id, alt_ref_type_id, date_sampled; method includes method_group_id, biblio_id)

### Phase 2: Metadata Completeness
- [x] Add sample group entities (description, description_type, sampling_context, lithology) — fully specified in `sead_standard_model.yml`
- [x] Add site entities (site_preservation_status, site_other_record) — fully specified in `sead_standard_model.yml`
- [x] Add dataset workflow (dataset_method, dataset_submission, dataset_submission_type) — fully specified in `sead_standard_model.yml`

### Phase 3: Taxonomy & Ecology
- [x] Add ecocode system (ecocode_system, ecocode_group, ecocode_definition, ecocode) — fully specified in `sead_standard_model.yml`
- [x] Add phenology (activity_type, season_type, season) — fully specified in `sead_standard_model.yml`
- [ ] Enhance taxa_tree_master specification (genus hierarchy, synonym support)

### Phase 4: Advanced Analysis
- [x] Add method classification (record_type, unit, data_type, data_type_group) — fully specified in `sead_standard_model.yml`
- [x] Add measured_value entity — fully specified in `sead_standard_model.yml`
- [ ] Add analysis value types (categorical, boolean, integer, numerical, date_range)
- [ ] Add project classification (project_type, project_stage)

## Success Criteria

1. **Arbodat Conformance**: All 54 entities in Arbodat project can be validated against target model
2. **SEAD Coverage**: 80%+ of commonly used SEAD Clearinghouse tables are specified
3. **Relationship Clarity**: All foreign keys documented with required/optional status
4. **Column Documentation**: Required columns specified for all entities
5. **Domain Organization**: Entities grouped into coherent domains (spatial, dating, taxonomy, etc.)

## Notes

- **Custom Entities**: Some Arbodat entities (natural_region, cultural_group, archaeological_period) appear specific to German archaeology. These may not belong in core SEAD model but should be documentable as extensions.
- **Legacy Tables**: Some SEAD tables appear deprecated or low-usage. Prioritize entities actively used in data submissions.
- **Naming Conventions**: Maintain consistency between `target_table` names and entity names (e.g., `sample` → `tbl_physical_samples`).
- **Bridge vs Via**: Use proper role classification and consider `via` attribute for many-to-many relationships.

## References

- SEAD Database Schema: `docs/sead/01_tables.sql`, `05_constraints.sql`, `07_comments.sql`
- Arbodat Project: `sead-tools/sead_shape_shifter/data/projects/arbodat/arbodat-rebecka/shapeshifter.yml`
- Current Target Model (Extended): `resources/target_models/sead_standard_model.yml`
- Base Target Model: `resources/target_models/sead_v2.yml`
- Target Model Guide: `docs/TARGET_MODEL_GUIDE.md`

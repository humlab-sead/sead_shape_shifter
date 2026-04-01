# Proposal: Complete SEAD v2 Target Model Specification

## Context

The current `sead_v2.yml` target model specification covers ~36 entities, but the actual SEAD Clearinghouse database contains 100+ tables. Analysis of the Arbodat Shape Shifter project reveals significant gaps in entity coverage that prevent effective conformance validation.

## Problem Statement

**Missing Coverage:** Many entities used in real-world SEAD data transformation projects (e.g., Arbodat) are not specified in the target model, resulting in:
- Inability to validate conformance for complete projects
- No formal specification for spatial coordinates, dating details, site properties, sample dimensions, or taxon metadata
- Inconsistent entity naming and relationship documentation

**Current Coverage (36 entities):**
Core: location, location_type, site, site_location, sample_group, sample, analysis_entity, dataset, method, project, citation, contact

Abundance: abundance, abundance_element, abundance_element_group, abundance_modification, abundance_property

Dating: relative_ages, relative_dating, geochronology, dating_lab

Taxonomy: taxa_tree_master, taxa_common_names

Classifiers: sample_type, sample_description_type, site_type, site_type_group, contact_type, method_group, modification_type, feature_type, feature

Bridges: dataset_contact, sample_feature

**Arbodat Project Uses (54 entities):**
Includes all above PLUS: coordinate_system, coordinate_method_dimension, dimension, sample_coordinate, dating (general), dating_period, archaeological_period, chronological_period, epoch, cultural_group, feature_property, feature_property_type, site_property, site_property_type, site_natural_region, natural_region, natural_region_group, dataset_submission, dataset_submission_type, abundance_property_type, identification_level, taxa (general taxon), taxa_use_categories, taxa_plant_sociological_behaviour

## Gap Analysis by Domain

### 1. Spatial/Coordinate Domain (High Priority)
**Missing:** coordinate_system, coordinate_method_dimension, dimension, sample_coordinate, sample_group_coordinate, site_natgridref

**Impact:** Cannot validate spatial metadata for samples or sample groups

**SEAD Tables:**
- `tbl_coordinate_method_dimensions` - coordinate measurement methods with dimensional constraints
- `tbl_dimensions` - measurement dimensions (X, Y, Z, depth, altitude, etc.)
- `tbl_sample_coordinates` - coordinates attached to physical samples
- `tbl_sample_group_coordinates` - coordinates attached to sample groups
- `tbl_site_natgridrefs` - national grid references for sites

### 2. Dating Domain (Medium Priority)
**Missing:** dating_material, dating_uncertainty, dating_period (analysis_entity → archaeological/chronological period), chronology, age_type

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
**Missing:** site_property, site_property_type, site_natural_region, natural_region, natural_region_group, site_preservation_status, site_other_records, site_reference

**Impact:** Cannot validate rich site metadata present in archaeological projects

**SEAD Tables:**
- `tbl_site_other_records` - additional site documentation/references
- Natural region data appears custom to Arbodat (German geographic classification)
- Site properties would follow description pattern

### 5. Sample Domain (High Priority)
**Missing:** sample_dimension, sample_horizon, sample_location, sample_location_type, sample_alt_ref, alt_ref_type, sample_note, sample_colour, colour

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
**Missing:** sample_group_description, sample_group_description_type, sample_group_dimension, sample_group_note, sample_group_reference, sampling_context, lithology

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
**Missing:** dataset_method (methods beyond primary method), dataset_submission, dataset_submission_type

**Impact:** Cannot validate multi-method datasets or submission workflow

**SEAD Tables:**
- `tbl_dataset_methods` - multiple methods per dataset
- `tbl_dataset_submissions` - submission tracking
- `tbl_dataset_submission_types` - submission type classifier

### 8. Taxon Domain (Medium Priority)
**Missing:** taxon (general), taxon_synonyms, taxon_common_name (vs taxa_common_names), ecocode, ecocode_definition, ecocode_group, ecocode_system, rdb (red data book), activity_type, season, taxon_measured_attributes

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
**Missing:** identification_level (abundance_ident_level), abundance_property_type

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
**Missing:** record_type, unit, data_type, data_type_group

**Impact:** Cannot validate method classification and result typing

**SEAD Tables:**
- `tbl_record_types` - type of record produced by method
- `tbl_units` - measurement units
- `tbl_data_types` - data type produced by method
- `tbl_data_type_groups` - data type grouping

## Proposed Additions

### Priority 1: Essential for Arbodat Conformance

```yaml
entities:
  # Spatial/Coordinate Domain
  dimension:
    role: classifier
    required: false
    description: Measurement dimension type (X, Y, Z, depth, altitude, thickness, etc.)
    domains: [spatial, physical-properties]
    target_table: tbl_dimensions
    public_id: dimension_id
    identity_columns: [dimension_name]
    columns:
      dimension_abbrev:
        required: true
        type: string
      dimension_name:
        required: true
        type: string
      method_group_id:
        type: integer
        nullable: true
      unit_id:
        type: integer
        nullable: true
    unique_sets:
      - [dimension_abbrev]
    foreign_keys:
      - entity: method_group
        required: false
      - entity: unit
        required: false

  coordinate_method_dimension:
    role: classifier
    required: false
    description: Coordinate measurement method with dimensional constraints
    domains: [spatial]
    target_table: tbl_coordinate_method_dimensions
    public_id: coordinate_method_dimension_id
    identity_columns: [method_id, dimension_id]
    columns:
      method_id:
        required: true
        type: integer
      dimension_id:
        required: true
        type: integer
      limit_upper:
        type: decimal
        nullable: true
      limit_lower:
        type: decimal
        nullable: true
    unique_sets:
      - [method_id, dimension_id]
    foreign_keys:
      - entity: method
        required: true
      - entity: dimension
        required: true

  sample_coordinate:
    role: fact
    required: false
    description: Spatial coordinate measurement for a physical sample
    domains: [spatial, sample-metadata]
    target_table: tbl_sample_coordinates
    public_id: sample_coordinate_id
    identity_columns: [physical_sample_id, coordinate_method_dimension_id]
    columns:
      physical_sample_id:
        required: true
        type: integer
      coordinate_method_dimension_id:
        required: true
        type: integer
      measurement:
        required: true
        type: decimal
      accuracy:
        type: decimal
        nullable: true
    foreign_keys:
      - entity: sample
        required: true
      - entity: coordinate_method_dimension
        required: true

  # Sample Metadata Domain
  alt_ref_type:
    role: classifier
    required: false
    description: Type of alternative reference (lab number, field ID, museum number)
    domains: [sample-metadata]
    target_table: tbl_alt_ref_types
    public_id: alt_ref_type_id
    identity_columns: [alt_ref_type]
    columns:
      alt_ref_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [alt_ref_type]

  sample_alt_ref:
    role: fact
    required: false
    description: Alternative reference identifier for a sample
    domains: [sample-metadata]
    target_table: tbl_sample_alt_refs
    public_id: sample_alt_ref_id
    identity_columns: [physical_sample_id, alt_ref_type_id, alt_ref]
    columns:
      physical_sample_id:
        required: true
        type: integer
      alt_ref_type_id:
        required: true
        type: integer
      alt_ref:
        required: true
        type: string
    unique_sets:
      - [physical_sample_id, alt_ref_type_id, alt_ref]
    foreign_keys:
      - entity: sample
        required: true
      - entity: alt_ref_type
        required: true

  sample_dimension:
    role: fact
    required: false
    description: Physical dimension measurement of a sample
    domains: [sample-metadata, physical-properties]
    target_table: tbl_sample_dimensions
    public_id: sample_dimension_id
    identity_columns: [physical_sample_id, dimension_id, method_id]
    columns:
      physical_sample_id:
        required: true
        type: integer
      dimension_id:
        required: true
        type: integer
      method_id:
        required: true
        type: integer
      dimension_value:
        required: true
        type: decimal
    foreign_keys:
      - entity: sample
        required: true
      - entity: dimension
        required: true
      - entity: method
        required: true

  # Abundance Domain
  identification_level:
    role: classifier
    required: false
    description: Taxonomic identification confidence level (Family, Genus, Species, cf. X)
    domains: [taxonomy, abundance]
    target_table: tbl_identification_levels
    public_id: identification_level_id
    identity_columns: [identification_level_abbrev]
    columns:
      identification_level_abbrev:
        required: true
        type: string
      identification_level_name:
        required: true
        type: string
      notes:
        type: string
        nullable: true
    unique_sets:
      - [identification_level_abbrev]

  abundance_ident_level:
    role: bridge
    required: false
    description: Links abundance records to identification confidence levels
    domains: [taxonomy, abundance]
    target_table: tbl_abundance_ident_levels
    public_id: abundance_ident_level_id
    identity_columns: [abundance_id, identification_level_id]
    columns:
      abundance_id:
        required: true
        type: integer
      identification_level_id:
        required: true
        type: integer
    unique_sets:
      - [abundance_id, identification_level_id]
    foreign_keys:
      - entity: abundance
        required: true
      - entity: identification_level
        required: true

  # Dating Domain
  dating_material:
    role: lookup
    required: false
    description: Material dated in geochronological analysis
    domains: [dating]
    target_table: tbl_dating_material
    public_id: dating_material_id
    identity_columns: [dating_material_name]
    columns:
      dating_material_name:
        required: true
        type: string
      description:
        type: string
        nullable: true
      abundance_element_id:
        type: integer
        nullable: true
    unique_sets:
      - [dating_material_name]
    foreign_keys:
      - entity: abundance_element
        required: false

  dating_uncertainty:
    role: classifier
    required: false
    description: Uncertainty qualifiers for dating results
    domains: [dating]
    target_table: tbl_dating_uncertainty
    public_id: dating_uncertainty_id
    identity_columns: [uncertainty]
    columns:
      uncertainty:
        required: true
        type: string
    unique_sets:
      - [uncertainty]

  age_type:
    role: classifier
    required: false
    description: Chronological notation system (AD, BC, BP, cal BP)
    domains: [dating]
    target_table: tbl_age_types
    public_id: age_type_id
    identity_columns: [age_type]
    columns:
      age_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [age_type]

  relative_age_type:
    role: classifier
    required: false
    description: Type of relative age system (archaeological period, geological epoch)
    domains: [dating]
    target_table: tbl_relative_age_types
    public_id: relative_age_type_id
    identity_columns: [age_type]
    columns:
      age_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [age_type]

  chronology:
    role: lookup
    required: false
    description: Chronological framework or dating system
    domains: [dating]
    target_table: tbl_chronologies
    public_id: chronology_id
    identity_columns: [chronology_name]
    columns:
      chronology_name:
        required: true
        type: string
      location_id:
        type: integer
        nullable: true
      notes:
        type: string
        nullable: true
    unique_sets:
      - [chronology_name]
    foreign_keys:
      - entity: location
        required: false
```

### Priority 2: Complete Sample Group & Site Metadata

```yaml
  # Sample Group Domain
  sample_group_description_type:
    role: classifier
    required: false
    description: Type of sample group description
    domains: [sample-metadata]
    target_table: tbl_sample_group_description_types
    public_id: sample_group_description_type_id
    identity_columns: [type_name]
    columns:
      type_name:
        required: true
        type: string
      type_description:
        type: string
        nullable: true
    unique_sets:
      - [type_name]

  sample_group_description:
    role: fact
    required: false
    description: Typed description attached to a sample group
    domains: [sample-metadata]
    target_table: tbl_sample_group_descriptions
    public_id: sample_group_description_id
    identity_columns: [sample_group_id, sample_group_description_type_id]
    columns:
      sample_group_id:
        required: true
        type: integer
      sample_group_description_type_id:
        required: true
        type: integer
      group_description:
        type: string
        nullable: true
    foreign_keys:
      - entity: sample_group
        required: true
      - entity: sample_group_description_type
        required: true

  sampling_context:
    role: classifier
    required: false
    description: Sampling context or strategy (archaeological excavation, core, etc.)
    domains: [sample-metadata]
    target_table: tbl_sample_group_sampling_contexts
    public_id: sampling_context_id
    identity_columns: [sampling_context]
    columns:
      sampling_context:
        required: true
        type: string
      description:
        type: string
        nullable: true
      sort_order:
        type: integer
        nullable: true
    unique_sets:
      - [sampling_context]

  lithology:
    role: fact
    required: false
    description: Lithological description of sediment layers in a sample group
    domains: [sample-metadata, geology]
    target_table: tbl_lithology
    public_id: lithology_id
    identity_columns: [sample_group_id, depth_top]
    columns:
      sample_group_id:
        required: true
        type: integer
      depth_top:
        required: true
        type: decimal
      depth_bottom:
        type: decimal
        nullable: true
      description:
        required: true
        type: string
      lower_boundary:
        type: string
        nullable: true
    foreign_keys:
      - entity: sample_group
        required: true

  # Site Domain
  site_preservation_status:
    role: classifier
    required: false
    description: Preservation status of archaeological site
    domains: [site-metadata]
    target_table: tbl_site_preservation_status
    public_id: site_preservation_status_id
    identity_columns: [preservation_status]
    columns:
      preservation_status:
        required: true
        type: string
      description:
        type: string
        nullable: true

  site_other_record:
    role: fact
    required: false
    description: Additional documentation or records for a site
    domains: [site-metadata, provenance]
    target_table: tbl_site_other_records
    public_id: site_other_records_id
    identity_columns: [site_id, biblio_id, record_type_id]
    columns:
      site_id:
        required: true
        type: integer
      biblio_id:
        type: integer
        nullable: true
      record_type_id:
        type: integer
        nullable: true
      description:
        type: string
        nullable: true
    foreign_keys:
      - entity: site
        required: true
      - entity: citation
        required: false
      - entity: record_type
        required: false
```

### Priority 3: Taxonomy & Ecology

```yaml
  # Taxon Domain
  ecocode_system:
    role: lookup
    required: false
    description: Ecological classification system (e.g., Ellenberg, Hill-Ellenberg)
    domains: [taxonomy, ecology]
    target_table: tbl_ecocode_systems
    public_id: ecocode_system_id
    identity_columns: [ecocode_system_name]
    columns:
      biblio_id:
        type: integer
        nullable: true
      definition:
        type: string
        nullable: true
      notes:
        type: string
        nullable: true
    foreign_keys:
      - entity: citation
        required: false

  ecocode_group:
    role: classifier
    required: false
    description: Ecological code category (moisture, nitrogen, light, temperature)
    domains: [taxonomy, ecology]
    target_table: tbl_ecocode_groups
    public_id: ecocode_group_id
    identity_columns: [ecocode_group_name]
    columns:
      ecocode_group_name:
        required: true
        type: string
      definition:
        type: string
        nullable: true
      abbreviation:
        type: string
        nullable: true
    unique_sets:
      - [ecocode_group_name]

  ecocode_definition:
    role: classifier
    required: false
    description: Specific ecocode value definition within a group and system
    domains: [taxonomy, ecology]
    target_table: tbl_ecocode_definitions
    public_id: ecocode_definition_id
    identity_columns: [ecocode_system_id, ecocode_group_id, abbreviation]
    columns:
      ecocode_system_id:
        required: true
        type: integer
      ecocode_group_id:
        required: true
        type: integer
      abbreviation:
        required: true
        type: string
      definition:
        type: string
        nullable: true
      sort_order:
        type: integer
        nullable: true
    unique_sets:
      - [ecocode_system_id, ecocode_group_id, abbreviation]
    foreign_keys:
      - entity: ecocode_system
        required: true
      - entity: ecocode_group
        required: true

  ecocode:
    role: fact
    required: false
    description: Ecological indicator value assigned to a taxon
    domains: [taxonomy, ecology]
    target_table: tbl_ecocodes
    public_id: ecocode_id
    identity_columns: [ecocode_definition_id, taxon_id]
    columns:
      ecocode_definition_id:
        required: true
        type: integer
      taxon_id:
        required: true
        type: integer
    unique_sets:
      - [ecocode_definition_id, taxon_id]
    foreign_keys:
      - entity: ecocode_definition
        required: true
      - entity: taxa_tree_master
        required: true

  activity_type:
    role: classifier
    required: false
    description: Life stage or phenological state (adult, flowering, fruiting)
    domains: [taxonomy, phenology]
    target_table: tbl_activity_types
    public_id: activity_type_id
    identity_columns: [activity_type]
    columns:
      activity_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [activity_type]

  season_type:
    role: classifier
    required: false
    description: Type of seasonal classification system
    domains: [phenology]
    target_table: tbl_season_types
    public_id: season_type_id
    identity_columns: [season_type]
    columns:
      season_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [season_type]

  season:
    role: classifier
    required: false
    description: Seasonal classification (spring, summer, early flowering, etc.)
    domains: [phenology]
    target_table: tbl_seasons
    public_id: season_id
    identity_columns: [season_type_id, season_name]
    columns:
      season_type_id:
        type: integer
        nullable: true
      season_type:
        type: string
        nullable: true
      season_name:
        required: true
        type: string
      sort_order:
        type: integer
        nullable: true
    foreign_keys:
      - entity: season_type
        required: false
```

### Priority 4: Method & Analysis Metadata

```yaml
  # Method Domain
  record_type:
    role: classifier
    required: false
    description: Type of record produced by analytical method
    domains: [methodology]
    target_table: tbl_record_types
    public_id: record_type_id
    identity_columns: [record_type_name]
    columns:
      record_type_name:
        required: true
        type: string
      record_type_description:
        type: string
        nullable: true
    unique_sets:
      - [record_type_name]

  unit:
    role: classifier
    required: false
    description: Measurement unit (mm, cm, grams, percent, ppm)
    domains: [methodology, physical-properties]
    target_table: tbl_units
    public_id: unit_id
    identity_columns: [unit_abbrev]
    columns:
      unit_abbrev:
        required: true
        type: string
      unit_name:
        type: string
        nullable: true
      description:
        type: string
        nullable: true
    unique_sets:
      - [unit_abbrev]

  data_type_group:
    role: classifier
    required: false
    description: Grouping of data types (abundance, measurement, observation)
    domains: [methodology]
    target_table: tbl_data_type_groups
    public_id: data_type_group_id
    identity_columns: [data_type_group_name]
    columns:
      data_type_group_name:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [data_type_group_name]

  data_type:
    role: classifier
    required: false
    description: Type of data produced by method (count, presence, MNI, percent)
    domains: [methodology]
    target_table: tbl_data_types
    public_id: data_type_id
    identity_columns: [data_type_name]
    columns:
      data_type_group_id:
        required: true
        type: integer
      data_type_name:
        required: true
        type: string
      definition:
        type: string
        nullable: true
    unique_sets:
      - [data_type_name]
    foreign_keys:
      - entity: data_type_group
        required: true

  # Dataset Domain
  dataset_method:
    role: bridge
    required: false
    description: Association of multiple methods with a dataset
    domains: [provenance]
    target_table: tbl_dataset_methods
    public_id: dataset_method_id
    identity_columns: [dataset_id, method_id]
    columns:
      dataset_id:
        required: true
        type: integer
      method_id:
        required: true
        type: integer
    unique_sets:
      - [dataset_id, method_id]
    foreign_keys:
      - entity: dataset
        required: true
      - entity: method
        required: true

  dataset_submission_type:
    role: classifier
    required: false
    description: Type of dataset submission (initial, update, correction)
    domains: [provenance]
    target_table: tbl_dataset_submission_types
    public_id: submission_type_id
    identity_columns: [submission_type]
    columns:
      submission_type:
        required: true
        type: string
      description:
        type: string
        nullable: true
    unique_sets:
      - [submission_type]

  dataset_submission:
    role: fact
    required: false
    description: Submission tracking for datasets
    domains: [provenance]
    target_table: tbl_dataset_submissions
    public_id: dataset_submission_id
    identity_columns: [dataset_id, submission_type_id, contact_id]
    columns:
      dataset_id:
        required: true
        type: integer
      submission_type_id:
        required: true
        type: integer
      contact_id:
        required: true
        type: integer
      submission_date:
        type: date
        nullable: true
      notes:
        type: string
        nullable: true
    foreign_keys:
      - entity: dataset
        required: true
      - entity: dataset_submission_type
        required: true
      - entity: contact
        required: true
```

## Implementation Plan

### Phase 1: Core Enhancements (Immediately needed for Arbodat)
- [ ] Add spatial/coordinate entities (dimension, coordinate_method_dimension, sample_coordinate)
- [ ] Add sample metadata entities (alt_ref_type, sample_alt_ref, sample_dimension)
- [ ] Add abundance precision (identification_level, abundance_ident_level)
- [ ] Add dating metadata (dating_material, dating_uncertainty, age_type, relative_age_type)
- [ ] Update existing entity specs with missing columns and FKs

### Phase 2: Metadata Completeness
- [ ] Add sample group entities (description, dimension, lithology, sampling_context)
- [ ] Add site entities (preservation_status, other_records)
- [ ] Add dataset workflow (dataset_method, dataset_submission, submission_type)

### Phase 3: Taxonomy & Ecology
- [ ] Add ecocode system (system, group, definition, ecocode)
- [ ] Add phenology (activity_type, season_type, season)
- [ ] Enhance taxa_tree_master specification

### Phase 4: Advanced Analysis
- [ ] Add method classification (record_type, unit, data_type, data_type_group)
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
- Current Target Model: `target_models/specs/sead_v2.yml`
- Target Model Guide: `docs/TARGET_MODEL_GUIDE.md`

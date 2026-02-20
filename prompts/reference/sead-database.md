# SEAD Database Reference Guide

> **Domain-Specific Reference**: This guide is for developing the SEAD ingester (`ingesters/sead/`) and SEAD-specific Shape Shifter projects. **Core Shape Shifter is schema-agnostic** and doesn't depend on SEAD. Use this reference when working with SEAD data imports or creating SEAD transformation configs.

Quick reference for SEAD (Strategic Environmental Archaeology Database) schema questions.

## Domain

**SEAD** is an archaeological and paleoecological database storing:
- Environmental proxy data (biological, geological, geochemical)
- Archaeological samples and analysis results
- Taxonomic abundance counts (insects, plants, animals)
- Dating information (radiocarbon, dendrochronology)
- Site and sample metadata
- Research datasets and publications

## Schema Conventions

### Naming Patterns
- **Tables**: `tbl_{entity_name}` (e.g., `tbl_sites`, `tbl_samples`)
- **Primary Keys**: `{entity_name}_id` (e.g., `site_id`, `sample_id`)
- **Timestamps**: `date_updated timestamp with time zone DEFAULT now()`
- **UUIDs**: `{entity_name}_uuid uuid DEFAULT uuid_generate_v4()`

### Common Columns
- All tables have integer primary key (bigint for large tables)
- Many tables include `date_updated` for audit tracking
- Reference tables include `description` text fields
- Some tables have UUID columns for external references

## Core Table Categories

### 1. Sample Hierarchy
```
tbl_sites
  └─ tbl_sample_groups
      └─ tbl_physical_samples
          └─ tbl_analysis_entities (virtual construct)
```

**Key Concept**: Analysis entities are **virtual constructs** enabling multiple proxies per physical sample.

### 2. Biological Proxies
- `tbl_abundances` - Species counts/presence per analysis entity
- `tbl_abundance_elements` - What was counted (MNI, seeds, leaves, etc.)
- `tbl_abundance_modifications` - Preservation state (carbonized, corroded)
- `tbl_taxa_tree_master` - Taxonomic hierarchy

### 3. Dating & Chronology
- `tbl_geochronology` - Radiocarbon and other absolute dates
- `tbl_dendro_dates` - Tree-ring dates
- `tbl_chronologies` - Named chronological frameworks
- `tbl_age_types` - Year notation systems (AD, BC, BP)

### 4. Analysis Methods
- `tbl_methods` - Analytical procedures
- `tbl_datasets` - Organized collections of analysis entities
- `tbl_dataset_methods` - Methods used in datasets
- `tbl_data_types` - Types of proxy data (e.g., pollen counts, isotopes)

### 5. Analysis Values (Generic System)
```
tbl_analysis_values (base table)
  ├─ tbl_analysis_boolean_values
  ├─ tbl_analysis_categorical_values
  ├─ tbl_analysis_integer_values
  ├─ tbl_analysis_numerical_values
  ├─ tbl_analysis_dating_ranges
  └─ tbl_analysis_identifiers
```

**Pattern**: Polymorphic value storage for different measurement types.

### 6. Reference/Lookup Tables
- `tbl_activity_types` - Life stages (adult, flowering)
- `tbl_colors` - Standard color references
- `tbl_feature_types` - Archaeological feature classifications
- `tbl_modification_types` - Specimen modifications
- `tbl_seasons` - Seasonal constraints

### 7. Metadata & Administration
- `tbl_biblio` - Publications and references
- `tbl_contacts` - Researchers and data contributors
- `tbl_dataset_contacts` - Dataset authorship
- `tbl_dataset_submissions` - Data submission tracking

## Critical Relationships

### Sample → Analysis Entity → Abundance
```sql
physical_sample 
  → analysis_entity (via dataset grouping)
    → abundance (species count)
      → taxon (what species)
      → abundance_element (what part counted)
```

### Analysis Entity Flexibility
One physical sample can have multiple analysis entities in different datasets:
- Pollen analysis dataset
- Insect analysis dataset  
- Macrofossil analysis dataset

Each dataset groups analysis entities by analytical method/proxy type.

### Taxonomic Resolution
```sql
abundance 
  → taxon_id (base identification)
  → abundance_ident_levels (cf. Family, cf. Genus, etc.)
```

Allows recording uncertainty in taxonomic identification.

## Common Query Patterns

### Find All Abundances for a Sample
```sql
SELECT 
    ps.sample_name,
    t.taxon_name,
    a.abundance,
    ae.element_name
FROM tbl_physical_samples ps
JOIN tbl_analysis_entities ae ON ae.physical_sample_id = ps.physical_sample_id
JOIN tbl_abundances a ON a.analysis_entity_id = ae.analysis_entity_id
JOIN tbl_taxa_tree_master t ON t.taxon_id = a.taxon_id
JOIN tbl_abundance_elements ae ON ae.abundance_element_id = a.abundance_element_id
WHERE ps.sample_name = 'ABC123';
```

### Get Dating for Analysis Entity
```sql
SELECT 
    ae.analysis_entity_id,
    aae.age,
    aae.age_older,
    aae.age_younger,
    c.chronology_name
FROM tbl_analysis_entities ae
JOIN tbl_analysis_entity_ages aae ON aae.analysis_entity_id = ae.analysis_entity_id
LEFT JOIN tbl_chronologies c ON c.chronology_id = aae.chronology_id;
```

## Important Notes

### Virtual vs Physical
- **Physical Samples**: Actual material from field/lab
- **Analysis Entities**: Virtual statistical samples (one physical sample → many analysis entities)
- **Datasets**: Logical groupings of analysis entities by research project/method

### Abundance Values
`tbl_abundances.abundance` can represent:
- Integer counts (standard)
- Presence indicator (1 = present)
- Categorical values (ordinal scales)
- Relative abundance (percentages)

**Data type determines interpretation** (see `tbl_data_types`).

### Age Ranges
Many tables use PostgreSQL `int4range` type for age ranges:
```sql
age_range int4range GENERATED ALWAYS AS (
    CASE
        WHEN (age_younger IS NULL AND age_older IS NULL) THEN NULL
        ELSE int4range(COALESCE(age_younger, age_older), COALESCE(age_older, age_younger) + 1)
    END
) STORED
```

### Variants
Several analysis value tables include `is_variant` boolean:
- Indicates alternative interpretations of the same measurement
- Allows recording multiple readings/interpretations per analysis

## Quick Reference: Key Tables

| Table | Purpose | Key Relationships |
|-------|---------|-------------------|
| `tbl_sites` | Archaeological/sampling sites | → sample_groups → physical_samples |
| `tbl_physical_samples` | Physical material samples | → analysis_entities (via dataset) |
| `tbl_analysis_entities` | Virtual statistical samples | → abundances, analysis_values |
| `tbl_abundances` | Species counts/presence | → taxon, analysis_entity |
| `tbl_taxa_tree_master` | Taxonomic hierarchy | ← abundances, ecocodes |
| `tbl_datasets` | Research datasets | → analysis_entities, methods |
| `tbl_geochronology` | Absolute dates | → analysis_entities |
| `tbl_methods` | Analytical procedures | ← dataset_methods |
| `tbl_biblio` | Publications | ← dataset_submissions, geochron_refs |

## Schema Comments

**Critical**: Table and column comments in `07_comments.sql` contain essential semantic information:
- Business logic not captured in structure
- Interpretation guidelines for values
- Historical context for design decisions
- Usage examples and constraints

**Always check comments** when interpreting unfamiliar tables/columns.

## Usage in Shape Shifter

When creating Shape Shifter configurations for SEAD:

1. **Identity**: Use SEAD primary keys as `public_id` (e.g., `site_id`, `sample_id`)
2. **Foreign Keys**: Match SEAD FK relationships in entity dependencies
3. **Data Sources**: Connect to SEAD PostgreSQL database (host: 130.239.57.54, port: 5433)
4. **Reconciliation**: Map local data → SEAD IDs using `mappings.yml`
5. **Fixed Entities**: SEAD lookup tables are candidates for fixed entities

## Common Questions Patterns

**Q: "How do I find all species for a site?"**  
A: Site → Sample Group → Physical Sample → Analysis Entity → Abundance → Taxon

**Q: "What's the difference between physical sample and analysis entity?"**  
A: Physical sample = actual material; analysis entity = virtual construct allowing multiple proxies per sample

**Q: "How are dates stored?"**  
A: Multiple systems: `tbl_geochronology` (absolute), `tbl_dendro_dates` (tree rings), `tbl_analysis_entity_ages` (derived)

**Q: "What are abundance elements?"**  
A: Defines what part was counted (whole organism, MNI, seed, leaf, etc.)

**Q: "How do I handle taxonomic uncertainty?"**  
A: Use `tbl_abundance_ident_levels` to record identification confidence (cf. Family, cf. Genus, etc.)

## Related Documentation
- [Entity Validation](../analysis/entity-validation.md) - For validating SEAD entities in Shape Shifter
- [Add Data Loader](../implementation/add-loader.md) - For connecting to SEAD database
- [YAML Review](../analysis/yaml-review.md) - For reviewing SEAD project configs

---
agent: ask
description: SEAD database schema reference — table hierarchy, naming conventions, and common FK patterns for SEAD ingester development
---

> **Domain-Specific Reference**: Use when working with the SEAD ingester (`ingesters/sead/`) or SEAD-specific Shape Shifter projects. Core Shape Shifter is schema-agnostic.

## Domain

**SEAD** (Strategic Environmental Archaeology Database) stores:
- Environmental proxy data (biological, geological, geochemical)
- Archaeological samples and analysis results
- Taxonomic abundance counts (insects, plants, animals)
- Dating information (radiocarbon, dendrochronology)
- Site and sample metadata

## Schema Conventions

### Naming Patterns
- **Tables**: `tbl_{entity_name}` (e.g., `tbl_sites`, `tbl_samples`)
- **Primary Keys**: `{entity_name}_id` (e.g., `site_id`, `sample_id`)
- **Timestamps**: `date_updated timestamp with time zone DEFAULT now()`
- **UUIDs**: `{entity_name}_uuid uuid DEFAULT uuid_generate_v4()`

## Core Table Categories

### Sample Hierarchy
```
tbl_sites
  └─ tbl_sample_groups
      └─ tbl_physical_samples
          └─ tbl_analysis_entities (virtual construct)
```

Analysis entities are **virtual constructs** — one physical sample can have multiple analysis entities across different datasets.

### Biological Proxies
- `tbl_abundances` — Species counts/presence per analysis entity
- `tbl_abundance_elements` — What was counted (MNI, seeds, leaves, etc.)
- `tbl_taxa_tree_master` — Taxonomic hierarchy

### Dating & Chronology
- `tbl_geochronology` — Radiocarbon and other absolute dates
- `tbl_dendro_dates` — Tree-ring dates
- `tbl_chronologies` — Named chronological frameworks

### Analysis Methods
- `tbl_methods` — Analytical procedures
- `tbl_datasets` — Organized collections of analysis entities
- `tbl_data_types` — Types of proxy data

### Analysis Values (Generic System)
```
tbl_analysis_values (base)
  ├─ tbl_analysis_boolean_values
  ├─ tbl_analysis_categorical_values
  ├─ tbl_analysis_integer_values
  ├─ tbl_analysis_numerical_values
  ├─ tbl_analysis_dating_ranges
  └─ tbl_analysis_identifiers
```

### Reference / Lookup Tables
- `tbl_activity_types`, `tbl_colors`, `tbl_feature_types`, `tbl_modification_types`, `tbl_seasons`

### Metadata & Administration
- `tbl_biblio` — Publications
- `tbl_contacts` — Researchers
- `tbl_dataset_submissions` — Data submission tracking

## Critical Relationships

```sql
-- Sample → Analysis Entity → Abundance
physical_sample
  → analysis_entity (via dataset grouping)
    → abundance (species count)
      → taxon
      → abundance_element (what part counted)
```

## Common FK Patterns

```sql
analysis_entities.physical_sample_id → physical_samples.physical_sample_id
abundances.analysis_entity_id        → analysis_entities.analysis_entity_id
abundances.taxon_id                  → taxa_tree_master.taxon_id
analysis_entities.dataset_id         → datasets.dataset_id
physical_samples.sample_group_id     → sample_groups.sample_group_id
sample_groups.site_id                → sites.site_id
```

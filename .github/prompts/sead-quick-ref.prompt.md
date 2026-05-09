---
agent: ask
description: Ultra-concise SEAD database lookup card — key tables, primary keys, and FK patterns
---

> **Domain-Specific Reference**: For SEAD ingester (`ingesters/sead/`) and SEAD project development. Core Shape Shifter is schema-agnostic.

## Core Hierarchy

```
tbl_sites
  └─ tbl_sample_groups
      └─ tbl_physical_samples (actual material)
          └─ tbl_analysis_entities (virtual — one physical → many analysis)
              └─ tbl_abundances (species counts)
                  └─ tbl_taxa_tree_master (taxonomy)
```

## Key Tables

| Table | Primary Key | Purpose |
|-------|-------------|---------|
| `tbl_sites` | `site_id` | Archaeological/sampling locations |
| `tbl_physical_samples` | `physical_sample_id` | Physical material samples |
| `tbl_analysis_entities` | `analysis_entity_id` | Virtual statistical samples |
| `tbl_abundances` | `abundance_id` | Species counts/presence |
| `tbl_taxa_tree_master` | `taxon_id` | Taxonomic hierarchy |
| `tbl_datasets` | `dataset_id` | Research dataset groupings |
| `tbl_methods` | `method_id` | Analytical procedures |
| `tbl_geochronology` | `geochron_id` | Absolute dates |
| `tbl_dendro_dates` | `dendro_date_id` | Tree-ring dates |
| `tbl_biblio` | `biblio_id` | Publications |

## Common FK Patterns

```sql
analysis_entities.physical_sample_id → physical_samples.physical_sample_id
abundances.analysis_entity_id        → analysis_entities.analysis_entity_id
abundances.taxon_id                  → taxa_tree_master.taxon_id
analysis_entities.dataset_id         → datasets.dataset_id
physical_samples.sample_group_id     → sample_groups.sample_group_id
sample_groups.site_id                → sites.site_id
```

## Naming Conventions
- Tables: `tbl_{name}`
- Primary Keys: `{name}_id`
- Foreign Keys: `{referenced_table_name}_id`
- Timestamps: `date_updated timestamp with time zone`
- UUIDs: `{name}_uuid uuid`

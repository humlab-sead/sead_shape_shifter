# SEAD Quick Reference Card

> **Domain-Specific Reference**: For SEAD ingester (`ingesters/sead/`) and SEAD project development. Core Shape Shifter is schema-agnostic.

Ultra-concise reference for SEAD database queries.

## Core Hierarchy

```
tbl_sites
  └─ tbl_sample_groups  
      └─ tbl_physical_samples (actual material)
          └─ tbl_analysis_entities (virtual - one physical → many analysis)
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
-- Physical Sample → Analysis Entity
analysis_entities.physical_sample_id → physical_samples.physical_sample_id

-- Analysis Entity → Abundance
abundances.analysis_entity_id → analysis_entities.analysis_entity_id

-- Abundance → Taxon
abundances.taxon_id → taxa_tree_master.taxon_id

-- Analysis Entity → Dataset
analysis_entities.dataset_id → datasets.dataset_id

-- Sample → Sample Group → Site
physical_samples.sample_group_id → sample_groups.sample_group_id
sample_groups.site_id → sites.site_id
```

## Naming Conventions

- Tables: `tbl_{name}` (e.g., `tbl_sites`)
- Primary Keys: `{name}_id` (e.g., `site_id`)
- Foreign Keys: `{referenced_table_name}_id`
- Timestamps: `date_updated timestamp with time zone`
- UUIDs: `{name}_uuid uuid`

## Critical Concepts

**Analysis Entity** = Virtual construct allowing multiple proxies per physical sample  
**Dataset** = Logical grouping of analysis entities by project/method  
**Abundance** = Species count OR presence OR categorical value (check `data_type`)  
**Element** = What was counted (MNI, seed, leaf, wing, etc.)

## Quick Queries

### Get All Species for Sample
```sql
SELECT t.taxon_name, a.abundance, ae.element_name
FROM tbl_physical_samples ps
JOIN tbl_analysis_entities ae ON ae.physical_sample_id = ps.physical_sample_id
JOIN tbl_abundances a ON a.analysis_entity_id = ae.analysis_entity_id
JOIN tbl_taxa_tree_master t ON t.taxon_id = a.taxon_id
JOIN tbl_abundance_elements ae ON ae.abundance_element_id = a.abundance_element_id
WHERE ps.sample_name = ?;
```

### Get Site Info with Samples
```sql
SELECT s.site_name, sg.sample_group_name, ps.sample_name
FROM tbl_sites s
JOIN tbl_sample_groups sg ON sg.site_id = s.site_id
JOIN tbl_physical_samples ps ON ps.sample_group_id = sg.sample_group_id
WHERE s.site_name = ?;
```

### Get Dataset Methods
```sql
SELECT d.dataset_name, m.method_name
FROM tbl_datasets d
JOIN tbl_dataset_methods dm ON dm.dataset_id = d.dataset_id
JOIN tbl_methods m ON m.method_id = dm.method_id
WHERE d.dataset_id = ?;
```

## Connection Info

**Production**: host=130.239.57.54, port=5433, dbname=sead_production  
**Test**: host=130.239.57.54, port=5433, dbname=sead_staging

## See Also

- [Full SEAD Database Guide](sead-database.md) - Complete reference with detailed explanations
- [Entity Validation](../analysis/entity-validation.md) - Validate SEAD entities in Shape Shifter

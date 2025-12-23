# Reconciliation Source Feature

## Overview

The `source` field in reconciliation entity specifications allows you to use different data sources for reconciliation than what exists in the final transformed entity. This is essential when reconciliation requires fields that are dropped during transformation or need enrichment from other sources.

## Use Cases

### 1. **Transformed Entity Loses Needed Fields**
Your main entity transformation might drop columns for cleanliness, but reconciliation needs them:

```yaml
# Main config - entity drops raw coordinates
entities:
  site:
    source: sites_table
    columns: [site_name, site_type]  # Drops lat/lon for final output
    
# Reconciliation config - needs coordinates
reconciliation:
  entities:
    site:
      source:
        data_source: "arbodat_data"
        type: sql
        query: "SELECT site_name, latitude, longitude, country FROM sites"
      keys: [site_name]
      property_mappings:
        latitude: latitude
        longitude: longitude
      remote:
        service_type: "site"
```

### 2. **Helper Entity with Enriched Data**
Create a temporary entity with extra fields just for reconciliation:

```yaml
# Main config - create enriched entity
entities:
  taxon:
    # Standard taxon entity
    source: taxa_table
    columns: [species]
    
  taxon_with_hierarchy:
    # Helper entity with additional fields
    source: taxa_lookup
    columns: [species, genus, family, author, common_name]

# Reconciliation config - use enriched data
reconciliation:
  entities:
    taxon:
      source: "taxon_with_hierarchy"  # Reference helper entity
      keys: [species]
      property_mappings:
        genus: genus
        family: family
      remote:
        service_type: "taxon"
```

### 3. **Join Multiple Tables**
Execute custom query joining multiple sources:

```yaml
reconciliation:
  entities:
    site:
      source:
        data_source: "main_db"
        type: sql
        query: |
          SELECT 
            s.site_name,
            s.site_code,
            c.latitude,
            c.longitude,
            l.country_name,
            l.region_name
          FROM sites s
          LEFT JOIN coordinates c ON s.site_id = c.site_id
          LEFT JOIN locations l ON s.location_id = l.location_id
          WHERE c.latitude IS NOT NULL
      keys: [site_name]
      property_mappings:
        latitude: latitude
        longitude: longitude
        country: country_name
      remote:
        service_type: "site"
```

## Source Field Options

### Option 1: Default (No Source)
```yaml
source: null  # or omit field entirely
```
Uses the entity's own preview data. Default behavior.

### Option 2: Reference Another Entity
```yaml
source: "entity_name"
```
Uses preview data from the named entity. Entity must exist in main configuration.

### Option 3: Custom SQL Query
```yaml
source:
  data_source: "data_source_name"  # Must exist in main config
  type: sql
  query: "SELECT ..."
```
Executes custom query against specified data source.

## Implementation Details

### Backend Resolution Logic

The `ReconciliationService._resolve_source_data()` method handles three cases:

1. **No source / empty / same as entity**: Returns entity preview data directly
2. **String source**: Fetches preview from named entity via `EntityPreviewService`
3. **Dict source**: Executes custom SQL via `SQLLoader`

### Available Fields

All fields referenced in `keys` and `property_mappings` must exist in the source data:

```yaml
# This will FAIL if source doesn't have 'latitude' column
site:
  source: "sites_without_coords"  # Missing latitude/longitude
  keys: [site_name]
  property_mappings:
    latitude: latitude  # ❌ Error - field not in source
```

### Performance Considerations

- **Entity reference**: Fast - reuses cached preview data
- **Custom query**: Slower - executes new SQL query
- Consider creating helper entities instead of custom queries when possible

## Common Patterns

### Pattern 1: Pre-filtered Data
```yaml
site_filtered:
  source:
    data_source: "sites_db"
    type: sql
    query: |
      SELECT * FROM sites
      WHERE status = 'verified'
      AND latitude IS NOT NULL
      AND country IS NOT NULL
```

### Pattern 2: Denormalized View
```yaml
taxon_flat:
  source:
    data_source: "taxonomy"
    type: sql
    query: |
      SELECT 
        t.species,
        t.genus,
        f.family_name as family,
        o.order_name as order,
        c.class_name as class
      FROM taxa t
      JOIN families f ON t.family_id = f.id
      JOIN orders o ON f.order_id = o.id
      JOIN classes c ON o.class_id = c.id
```

### Pattern 3: Computed Columns
```yaml
reference_formatted:
  source:
    data_source: "bibliography"
    type: sql
    query: |
      SELECT 
        citation_id,
        title,
        CONCAT(author_last, ', ', author_first) as authors,
        YEAR(publication_date) as year,
        doi
      FROM references
```

## Best Practices

1. **Prefer entity references over custom queries** when possible for better performance
2. **Document helper entities** clearly in main config to indicate they're for reconciliation
3. **Keep queries simple** - complex joins slow down reconciliation
4. **Filter early** - add WHERE clauses to reduce data volume
5. **Test queries separately** before adding to reconciliation config
6. **Verify field names** match between source and property_mappings

## Troubleshooting

### Error: "Source entity 'X' not found"
- Verify entity name exists in main configuration
- Check for typos in entity name
- Ensure entity is processed before reconciliation runs

### Error: "Column 'X' not found in source data"
- Query the source directly to verify available columns
- Check property_mappings references correct column names
- Ensure custom query includes all needed columns

### Poor Performance
- Reduce rows with WHERE clauses in custom queries
- Add indexes to source database tables
- Consider creating a materialized view for complex joins
- Use entity references instead of custom queries when possible

## See Also

- [Reconciliation Setup Guide](RECONCILIATION_SETUP_GUIDE.md)
- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [Entity Preview Documentation](SYSTEM_DOCUMENTATION.md#entity-preview)

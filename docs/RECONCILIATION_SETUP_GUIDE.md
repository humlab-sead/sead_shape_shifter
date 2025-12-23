# Reconciliation Setup Guide

This guide explains how to set up and use the entity reconciliation feature in Shape Shifter to map source data entities to SEAD database IDs.

## Overview

The reconciliation feature helps you map source entity values (e.g., "Oak", "Birch") to corresponding SEAD database entity IDs using an OpenRefine-compatible reconciliation service. It supports both automated matching (based on confidence thresholds) and manual review of uncertain matches.

## Prerequisites

1. **OpenRefine Reconciliation Service** - You must have a reconciliation service running (default: `http://localhost:8000`)
2. **Configuration File** - A Shape Shifter configuration file must exist
3. **Entity Preview Data** - The entity you want to reconcile must have preview data available

## Setup Steps

### 1. Start the Reconciliation Service

Ensure your OpenRefine reconciliation service is running:

```bash
# Example: Start your reconciliation service
# The service should be accessible at http://localhost:8000 (or configure a different URL)
```

### 2. Create Reconciliation Configuration

Create a YAML file named `{configuration-name}-reconciliation.yml` in the `input/` directory alongside your main configuration file.

**Example: `arbodat-reconciliation.yml`**

```yaml
# Reconciliation service configuration
service_url: "http://localhost:8000"  # OpenRefine reconciliation service URL

# Entity-specific reconciliation specifications
entities:
  
  # Example 1: Site reconciliation using entity preview (default)
  site:
    source: null  # Use site entity's own preview data
    
    keys:
      - site_name      # Primary key field(s) used to build query string
    
    property_mappings:
      # Map reconciliation service property IDs to source column names
      latitude: lat         # Service property 'latitude' -> source column 'lat'
      longitude: lon        # Service property 'longitude' -> source column 'lon'
      country: country_name # Service property 'country' -> source column 'country_name'
      national_id: site_id  # Service property 'national_id' -> source column 'site_id'
    
    remote:
      service_type: "site"  # Must match service defaultTypes ID (e.g., 'site', 'taxon')
                            # If null/empty, reconciliation is disabled for this entity
    
    auto_accept_threshold: 0.95   # Auto-accept matches with ≥95% confidence
    review_threshold: 0.70        # Flag matches 70-95% for manual review
    
    mapping: []  # Initial mappings (populated by auto-reconcile)

  # Example 2: Taxon reconciliation using another entity's data
  taxon:
    source: "taxon_with_hierarchy"  # Use data from taxon_with_hierarchy entity
    
    keys:
      - species      # Primary matching field
    
    property_mappings:
      genus: genus_name      # Service 'genus' -> source 'genus_name'
      family: family_name    # Service 'family' -> source 'family_name'
      scientific_name: full_name  # Service 'scientific_name' -> source 'full_name'
    
    remote:
      service_type: "taxon"  # Service entity type
    
    auto_accept_threshold: 0.90
    review_threshold: 0.65
    
    mapping: []

  # Example 3: Site reconciliation using custom SQL query
  site_with_coords:
    source:
      data_source: "arbodat_data"  # Data source from main config
      type: sql
      query: |
        SELECT 
          Fustel AS site_name,
          EVNr AS national_site_id,
          rWert AS latitude,
          hWert AS longitude,
          Ort AS locality
        FROM Projekte
        WHERE rWert IS NOT NULL
    
    keys:
      - site_name
    
    property_mappings:
      latitude: latitude
      longitude: longitude
      national_id: national_site_id
      place_name: locality
    
    remote:
      service_type: "site"
    
    auto_accept_threshold: 0.95
    review_threshold: 0.70
    
    mapping: []
```

### 3. Include Reconciliation in Main Configuration

Add an `@include` directive to your main configuration file to reference the reconciliation configuration:

**Example: `arbodat.yml`**

```yaml
# ... existing configuration ...

entities:
  taxon:
    # ... entity definition ...
  
  sample_type:
    # ... entity definition ...

# Include reconciliation configuration
reconciliation:
  @include: "arbodat-reconciliation.yml"
```

### 4. Configuration Reference

#### Service Configuration

```yaml
service_url: "http://localhost:8000"  # Required: Reconciliation service base URL
```

#### Entity Specification Fields

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `source` | ❌ | Data source for reconciliation (see Source Options below) | `null`, `"taxon_enriched"`, or `{data_source: "...", type: "sql", query: "..."}` |
| `keys` | ✅ | Primary key field(s) used to build query string | `["site_name"]` or `["species"]` |
| `property_mappings` | ❌ | Map service property IDs to source columns | `{"latitude": "lat", "genus": "genus_name"}` |
| `remote.service_type` | ❌ | Service entity type ID (from service defaultTypes) | `"site"`, `"taxon"` |
| `auto_accept_threshold` | ❌ | Auto-accept threshold (0.0-1.0, default: 0.95) | `0.95` |
| `review_threshold` | ❌ | Review threshold (0.0-1.0, default: 0.70) | `0.70` |
| `mapping` | ✅ | List of mappings (auto-populated) | `[]` |

**Important**: If `remote.service_type` is `null` or empty, reconciliation is disabled for that entity.

#### Source Options

The `source` field determines where reconciliation data comes from:

**Option 1: Use Entity Preview (Default)**
```yaml
source: null  # or empty, or same as entity name
```
Uses the entity's own preview data.

**Option 2: Use Another Entity**
```yaml
source: "taxon_enriched"  # Entity name
```
Uses preview data from another entity. Useful when you have a helper entity with additional fields needed for reconciliation.

**Option 3: Custom SQL Query**
```yaml
source:
  data_source: "arbodat_data"  # Data source from main config
  type: sql
  query: |
    SELECT site_name, latitude, longitude, country
    FROM sites
    WHERE latitude IS NOT NULL
```
Executes a custom query to get reconciliation data with specific fields not in the transformed entity.

#### Available Service Types

Based on the SEAD reconciliation service manifest:
- `bibliographic_reference` - Bibliographic References
- `country` - Countries
- `data_type` - Data Types  
- `dimension` - Dimensions
- `feature_type` - Feature Types
- `geonames` - GeoNames Places
- `location` - Locations & Places
- `method` - Methods
- `modification_type` - Modification Types
- `sampling_context` - Sampling Contexts
- `site` - Sites
- `administrative_region` - Sub-country administrative regions
- `taxon` - Taxa

#### Available Properties (by Entity Type)

**Site Properties:**
- `latitude` - Geographic latitude (WGS84)
- `longitude` - Geographic longitude (WGS84)
- `country` - Country name
- `national_id` - National site identifier
- `place_name` - Geographic place/locality name

**Taxon Properties:**
- `scientific_name` - Full taxonomic name
- `genus` - Genus name
- `species` - Species name
- `family` - Family name

**Bibliographic Reference Properties:**
- `doi` - Digital Object Identifier
- `isbn` - International Standard Book Number
- `title` - Title of work
- `year` - Publication year
- `authors` - Authors
- `full_reference` - Full citation
- `bugs_reference` - BugsCEP reference

**Method Properties:**
- `method_abbreviation` - Method abbreviation

**Dimension Properties:**
- `dimension_abbreviation` - Dimension abbreviation

**Modification Type Properties:**
- `description` - Description

#### Mapping Structure (Auto-generated)

```yaml
mapping:
  - source_values:
      - "Quercus robur"  # Matches key order (species)
    sead_id: 12345
    confidence: 0.985  # 98.5%
    notes: "Auto-matched: European Oak"
    created_by: "system"
    
  - source_values:
      - "Unknown oak sp."
    sead_id: 12300
    confidence: 0.72  # 72%
    notes: "Manually verified - generic oak"
    created_by: "user"
```

## Using the Reconciliation UI

### 1. Navigate to Reconciliation Tab

1. Open your configuration in the Shape Shifter web UI
2. Click the **Reconciliation** tab (between Dependencies and Data Sources)

### 2. Select Entity

1. Choose an entity from the dropdown (only entities with reconciliation specs appear)
2. Review the reconciliation specification details:
   - **Keys**: Primary matching columns (used in query string)
   - **Properties**: Property mappings (property_id→source_column)
   - **Service Type**: Reconciliation entity type from service
   - **Existing Mappings**: Number of previously saved mappings

### 3. Run Auto-Reconciliation

1. Click the **Auto-Reconcile** button
2. The system will:
   - Fetch entity preview data
   - Query the reconciliation service for each unique key combination
   - Auto-accept matches with confidence ≥ auto_accept threshold
   - Flag matches for review between review and auto_accept thresholds
   - Mark low-confidence matches as needing manual mapping

3. Review the results:
   - **Green rows**: Auto-matched (high confidence)
   - **Yellow rows**: Need review (medium confidence)
   - **Red rows**: Unmatched or low confidence

### 4. Review and Edit Mappings

#### Inline Editing

- Click on a **SEAD ID** cell to edit the ID directly
- Click on a **Notes** cell to add notes or context
- Changes are tracked; click **Save Changes** when ready

#### Review Candidates

1. Click the **magnifying glass icon** in the Actions column (shows candidate count)
2. Review candidate matches with confidence scores
3. Select the correct candidate
4. Click **Accept** to apply the mapping

### 5. Save Changes

1. Click **Save Changes** in the toolbar
2. Mappings are persisted to the `{config}-reconciliation.yml` file
3. Mappings are preserved across sessions

## Workflow Best Practices

### 1. Iterative Reconciliation

- Start with auto-reconcile to handle high-confidence matches
- Review yellow-flagged items (medium confidence)
- Manually map red items (low confidence or no match)
- Save incrementally to avoid losing work

### 2. Using Notes

Add notes to mappings for:
- **Manual decisions**: "Generic species, mapped to genus-level ID"
- **Uncertainty**: "Tentative match - verify with domain expert"
- **Data issues**: "Typo in source data: 'Qurcus' → Quercus"

### 3. Property Mapping Strategy

Choose properties based on available data and entity type:

**For Sites:**
- Always include geographic coordinates if available (`latitude`, `longitude`)
- Add `country` or `place_name` for location context
- Include `national_id` for official identifiers

**For Taxa:**
- Use hierarchical properties (`genus`, `family`) to improve matching
- Include `scientific_name` for full taxonomic name
- Species-only names may need genus context

**For References:**
- Structured identifiers (`doi`, `isbn`) give best matches
- Include `year` and `authors` for disambiguation
- `full_reference` for complete citation matching

### 4. Handling Unmatched Items

For items with no candidates or very low confidence:

1. **Check source data quality**: Verify spelling, formatting
2. **Add more properties**: Include additional property_mappings for better context
3. **Verify service type**: Ensure `service_type` matches available types
4. **Manual research**: Look up correct SEAD ID in database
5. **Create new entities**: If entity doesn't exist in SEAD, coordinate with admins

## Configuration Examples

### Simple Reconciliation (Using Entity Preview)

```yaml
entities:
  country:
    source: null  # Use country entity preview
    keys:
      - country_name
    remote:
      service_type: "country"
    mapping: []
```

### Using Another Entity's Data

```yaml
# Main config has a helper entity with extra fields
entities:
  # Helper entity with enriched taxon data
  taxon_enriched:
    source: taxa_lookup
    keys: ["species"]
    columns: ["species", "genus", "family", "author"]
    # ... other config
  
  # Reconciliation entity uses helper's richer data
  taxon:
    source: "taxon_enriched"  # Use enriched entity
    keys:
      - species
    property_mappings:
      genus: genus
      family: family
      scientific_name: species
    remote:
      service_type: "taxon"
    mapping: []
```

### Custom SQL Query Source

```yaml
entities:
  site:
    source:
      data_source: "arbodat_data"
      type: sql
      query: |
        SELECT 
          s.Fustel AS site_name,
          s.EVNr AS national_id,
          s.rWert AS latitude,
          s.hWert AS longitude,
          l.Ort AS locality,
          l.Land AS country
        FROM Projekte s
        LEFT JOIN Locations l ON s.location_id = l.id
        WHERE s.rWert IS NOT NULL
    
    keys:
      - site_name
    
    property_mappings:
      latitude: latitude
      longitude: longitude
      country: country
      national_id: national_id
      place_name: locality
    
    remote:
      service_type: "site"
    
    auto_accept_threshold: 0.95
    review_threshold: 0.70
    
    mapping: []
```

### Complex Multi-Source Example

```yaml
entities:
  # Simple entity uses own data
  country:
    source: null
    keys: [country_name]
    remote:
      service_type: "country"
    mapping: []
  
  # Entity references another entity
  taxon:
    source: "taxon_with_authors"
    keys: [species]
    property_mappings:
      genus: genus_col
      family: family_col
    remote:
      service_type: "taxon"
    mapping: []
  
  # Entity uses custom query for maximum control
  bibliographic_reference:
    source:
      data_source: "bibliography_db"
      type: sql
      query: |
        SELECT DISTINCT
          citation,
          doi,
          title,
          YEAR(pub_date) as year,
          authors
        FROM references
        WHERE doi IS NOT NULL OR isbn IS NOT NULL
    
    keys: [citation]
    property_mappings:
      doi: doi
      title: title
      year: year
      authors: authors
    remote:
      service_type: "bibliographic_reference"
    auto_accept_threshold: 0.98
    mapping: []
```

## Troubleshooting

### Service Connection Issues

**Problem**: Cannot connect to reconciliation service

**Solutions**:
- Verify service is running: `curl http://localhost:8000`
- Check `service.url` in reconciliation config
- Ensure no firewall blocking localhost:8000

### No Candidates Returned

**Problem**: Auto-reconcile returns no candidates

**Solutions**:
- Verify `remote.service_type` matches available service types (see list above)
- Check entity has preview data available
- Inspect reconciliation service logs for errors
- Test service directly with sample query
- Verify property IDs in `property_mappings` match service properties

### Low Confidence Scores

**Problem**: All matches have low confidence

**Solutions**:
- Add more property mappings to improve matching accuracy
- Check for data quality issues (spelling, formatting, missing values)
- Verify reconciliation service uses correct matching algorithm
- Consider lowering review threshold temporarily
- Use more specific key fields that uniquely identify entities

### Mappings Not Persisting

**Problem**: Changes lost after refresh

**Solutions**:
- Ensure you clicked **Save Changes** button
- Check file permissions on `input/{config}-reconciliation.yml`
- Verify backend API is running (port 8012)
- Check browser console for API errors

## Advanced Configuration

### Property Mapping Reference

Consult your reconciliation service manifest (`GET /reconcile`) for the complete list of available properties. The `extend.property_settings` section lists all properties with:
- Property ID (used in `property_mappings`)
- Label and help text
- Applicable entity types
- Data type and constraints

Example checking service manifest:
```bash
curl http://localhost:8000/reconcile | jq '.extend.property_settings'
```

### Multiple Reconciliation Services

Create separate reconciliation files for different data sources:

```yaml
# arbodat-reconciliation.yml
service_url: "http://localhost:8000"
entities:
  taxon:
    keys: [species]
    property_mappings:
      genus: genus_col
      family: family_col
    remote:
      service_type: "taxon"
    mapping: []

# ceramics-reconciliation.yml  
service_url: "http://ceramic-service:9000"
entities:
  ceramic_type:
    keys: [type_name]
    property_mappings:
      description: type_desc
    remote:
      service_type: "artifact_type"
    mapping: []
```

Include both in main config:

```yaml
reconciliation:
  arbodat:
    @include: "arbodat-reconciliation.yml"
  ceramics:
    @include: "ceramics-reconciliation.yml"
```

## API Reference

### Auto-Reconcile Endpoint

```
POST /api/v1/configurations/{config_name}/reconciliation/{entity_name}/auto-reconcile
```

Fetches entity data, queries reconciliation service, and auto-accepts high-confidence matches.

### Update Mapping Endpoint

```
POST /api/v1/configurations/{config_name}/reconciliation/{entity_name}/mapping
```

Manually create or update a mapping for specific source values.

### Suggest Entities Endpoint

```
GET /api/v1/configurations/{config_name}/reconciliation/{entity_name}/suggest?prefix={prefix}
```

Autocomplete suggestions for SEAD entity names.

## See Also

- [OpenRefine Reconciliation API Specification](https://reconciliation-api.github.io/specs/latest/)
- [Configuration Guide](CONFIGURATION_GUIDE.md)
- [Backend API Documentation](BACKEND_API.md)
- [Development Guide](DEVELOPMENT_GUIDE.md)

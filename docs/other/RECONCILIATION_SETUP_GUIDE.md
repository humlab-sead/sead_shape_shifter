# Reconciliation Setup Guide

This guide explains how to set up and use the entity reconciliation feature in Shape Shifter to map source data entities to SEAD database IDs.

## Overview

The reconciliation feature maps local source values (for example "Oak" or "Birch") to records in SEAD through an OpenRefine-compatible reconciliation service. The service proposes candidates; a reviewer accepts, rejects, or marks each row local-only. Accepted decisions are exported into the mapping sidecar, and normalization applies them.

Candidate scores and thresholds help a reviewer prioritize rows. They never accept a candidate.

## How Reconciliation Works with Identity System

Shape Shifter uses a **three-tier identity system** where reconciliation fits into the global scope:

1. **`system_id`** (Local): Auto-incrementing sequential IDs (1, 2, 3...) used for all FK relationships
2. **`keys`** (Business): Source data identifiers used for matching during reconciliation
3. **`public_id`** (Global): Target SEAD column name; holds reconciled SEAD IDs from the mapping sidecar (`<project>-mapping.yml`)

**Reconciliation Workflow:**
```
Source Data          Reconciliation Service       Mapping Sidecar        Final Export
─────────────        ─────────────────────        ───────────────        ────────────
location_name   →    Match to SEAD entities  →    local → remote    →   location_id
"Norway"             confidence: 0.98             "Norway": 162          162 (SEAD)
"Sweden"             confidence: 1.00             "Sweden": 205          205 (SEAD)

```

**Key Principle:** Reconciliation creates mappings (`business_key → SEAD_ID`) stored in the mapping sidecar (`<project>-mapping.yml`). During processing, these mappings are applied to populate the `public_id` column with SEAD IDs. FK relationships always use local `system_id` values.

## Prerequisites

1. **OpenRefine Reconciliation Service** - A reconciliation service must be running and reachable from the backend (default: `http://localhost:8000`)
2. **Project File** - A saved Shape Shifter project must exist
3. **Entity Rows** - The entity or source selected in the specification must produce rows
4. **Backend** - The Shape Shifter backend must be running (default: `http://localhost:8012`)

## Setup Steps

### 1. Confirm the Reconciliation Service

Check the service directly, then check the backend's view of it:

```bash
# The service answers with its OpenRefine manifest
curl http://localhost:8000/reconcile

# The backend reports whether it can reach the service
curl http://localhost:8012/api/v1/reconciliation/health
```

The Reconciliation tab shows **Online** with a supported-type count when the backend can reach the service.

### 2. Create or Open the Reconciliation Catalog

The reconciliation catalog is a separate file, not part of `shapeshifter.yml`. It lives in the project folder as `<project>-reconciliation.yml`, which for the default layout is:

```text
data/projects/<project>/<project>-reconciliation.yml
```

The **Reconciliation → Configuration** tab creates and edits this file for you. Add one specification per entity and target field, either through **Add Specification** or in the **YAML** tab.

The catalog is keyed by entity name, then by target field:

```yaml
# Reconciliation service configuration
service_url: "http://localhost:8000"  # OpenRefine reconciliation service URL

# Entity-specific reconciliation specifications
entities:
  # Example 1: Site reconciliation using entity preview (default)
  site:
    site_name:              # target field
      source: null          # null = use the entity's own preview rows
      property_mappings:
        # Map reconciliation service property IDs to source column names
        latitude: lat
        longitude: lon
        country: country_name
        national_id: site_id
      remote:
        service_type: "site"  # Must appear in supportedTypes from GET /reconcile
        columns: []
      auto_accept_threshold: 0.95
      review_threshold: 0.70
      mapping: []

  # Example 2: Taxon reconciliation using another entity's data
  taxon:
    species:                              # target field
      source: "taxon_with_hierarchy"      # use rows from another entity
      property_mappings:
        genus: genus_name
        family: family_name
        scientific_name: full_name
      remote:
        service_type: "taxon"
        columns: []
      auto_accept_threshold: 0.90
      review_threshold: 0.65
      mapping: []

  # Example 3: Site reconciliation using a custom SQL query
  site_with_coords:
    site_name:                            # target field
      source:
        data_source: "arbodat_data"       # Data source from main config
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
      property_mappings:
        latitude: latitude
        longitude: longitude
        national_id: national_site_id
        place_name: locality
      remote:
        service_type: "site"
        columns: []
      auto_accept_threshold: 0.95
      review_threshold: 0.70
      mapping: []
```

### 3. How the Catalog Is Found

The project does not reference the catalog from `shapeshifter.yml`. Shape Shifter looks for `<project>-reconciliation.yml` inside the project folder:

```text
data/projects/<project>/<project>-reconciliation.yml
```

There is no `@include` entry and no `reconciliation:` block in the project file. Saving through the Reconciliation tab writes the catalog to that path.

When the file is missing, Shape Shifter starts with an empty catalog for the project.

### 4. Project Reference

#### Service Project

```yaml
service_url: "http://localhost:8000"  # Required: Reconciliation service base URL
```

#### Entity Specification Fields

Each specification is stored under `entities.<entity_name>.<target_field>`. The entity name and target field are the key; the remaining fields configure matching.

| Field | Required | Description | Example |
|-------|----------|-------------|---------|
| `source` | ❌ | Rows used for matching (see Source Options below) | `null`, `"taxon_enriched"`, or `{data_source: "...", type: "sql", query: "..."}` |
| `property_mappings` | ❌ | Maps a service property to a source column | `{"latitude": "lat", "genus": "genus_name"}` |
| `remote.service_type` | ❌ | Service entity type; must appear in the manifest's `supportedTypes` | `"site"`, `"feature_type"`, `"location"` |
| `remote.columns` | ❌ | Additional columns requested from the service | `[]` |
| `auto_accept_threshold` | ❌ | Retained for compatibility; displayed but never accepts a candidate | `0.95` |
| `review_threshold` | ❌ | Flags low-scoring rows for attention | `0.70` |
| `mapping` | ❌ | Review decisions for this specification | `[]` |

There is no `keys` field. The search value comes from the target field, and the row is identified by its encoded business key from the entity's configured keys.

**Important**: If `remote.service_type` is `null` or empty, reconciliation is disabled for that entity.

#### Source Options

The `source` field determines where reconciliation rows come from:

**Option 1: Use Entity Preview (Default)**
```yaml
source: null  # or omit the field
```
Uses the entity's own preview rows.

**Option 2: Use Another Entity**
```yaml
source: "taxon_enriched"  # Entity name
```
Uses preview rows from another entity. Useful when you have a helper entity with additional fields needed for reconciliation. Column checks run against that entity instead of the reconciled entity.

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
Executes a custom query to get reconciliation rows with specific fields. Column checks are skipped for this option, because the columns are defined inside the query.

#### Available Service Types

`remote.service_type` must appear in the service manifest's `reconciliation.supportedTypes` list. That list is the authoritative set of implemented reconciliation types; `defaultTypes` only supplies OpenRefine display names and may include types without matching support.

```bash
curl http://localhost:8000/reconcile | jq '.reconciliation.supportedTypes'
```

The current service contract implements, for example, `site`, `feature_type`, and `location`. Do not copy a type from `defaultTypes`; check the manifest at the time you configure the specification.

#### Available Properties (by Entity Type)

The manifest's `extend.property_settings` entries declare properties. A property applies to a service type when that type appears in the entry's `entity_types` list; the entry `name` is the ID used as a `property_mappings` key.

```bash
curl http://localhost:8000/reconcile | jq '.extend.property_settings'
```

A supported type with no property entries is valid: it reconciles on the search label alone. Do not select properties from a fixed per-type list; older documentation that listed them by type is replaced by this manifest rule.

#### Decision Record Shape

Each entry in `mapping` records one review decision. The catalog stores decisions; the exported links are written to a separate mapping sidecar.

```yaml
mapping:
  - local_key_value: undecided        # encoded ordered business key
    source_value: "Slöinge Raä 114"   # search label, not row identity
    status: proposed                  # proposed | accepted | rejected | local-only
    candidates:
      - id: https://w3id.org/sead/id/site/1
        name: Slöinge Raä 114
        score: 100.0
        match: true

  - local_key_value: undecided
    source_value: "Slöinge Raä 114"
    status: accepted
    target_id: 1
    candidate_id: https://w3id.org/sead/id/site/1
    confidence: 1.0
    notes: "Confirmed against the excavation report"
```

A decision with `status: accepted` must carry both `target_id` and `candidate_id`. Only an accepted decision may carry them. The mapping sidecar, not this catalog, holds the links that normalization applies; see [Reconciliation Workflow](RECONCILIATION_WORKFLOW.md).

## Specification Validation

The reconciliation UI automatically validates each specification and displays the validation status in the specifications list. This helps identify configuration errors before running reconciliation.

### Validation Status Indicators

Each specification shows a status icon:

- ✅ **Green checkmark**: Valid - specification is correctly configured
- ⚠️ **Yellow warning**: Warning - specification has potential issues but may still work
- ❌ **Red error**: Error - specification has critical issues preventing reconciliation

Hover over the status icon to see detailed validation messages.

### Validation Checks

The system validates specifications against the **actual entity preview data**, ensuring that all referenced columns exist after all transformations (filtering, linking, unnesting, mapping):

1. **Entity Existence**: Verifies the entity exists in the project configuration
2. **Target Field Validation**: Confirms the `target_field` exists in the entity's columns
3. **Property Mappings**: Checks that all source columns in property_mappings exist

### Column Types Checked

Validation considers all five types of columns available in the reconciliation process:

1. **Keys** (`entity.keys`) - Primary identifier columns from entity configuration
2. **Regular Columns** (`entity.columns`) - Standard data columns from entity configuration
3. **Extra Columns** (`entity.extra_columns`) - Additional computed or derived columns
4. **Foreign Key Columns** (`entity.foreign_keys[].local_keys`) - Columns from FK join relationships
5. **Unnest Columns** (`entity.unnest.var_name`, `entity.unnest.value_name`) - Variable and value columns from pivot/melt operations

This comprehensive validation ensures that columns added through transformations (like unnesting wide-format data or joining foreign key tables) are properly recognized.

### Common Validation Errors

#### Missing Entity
```
Error: Entity 'unknown_entity' not found in project
```
**Solution**: Verify entity name matches exactly (case-sensitive), or create the entity in project configuration.

#### Invalid Target Field
```
Error: Target field 'taxon_id' not found in entity 'taxon'. Available fields: species, genus, family
```
**Solution**: Update `target_field` to match an available column name, or add the column to entity configuration.

#### Invalid Property Mapping
```
Warning: Property mapping 'latitude' references non-existent column 'lat'. Available fields: site_name, longitude, country
```
**Solution**: Correct the property mapping to use an existing column name (`latitude: latitude` instead of `latitude: lat`), or add the column to entity configuration.

### API-Based Validation

Validation uses the entity preview API (`/api/v1/entities/preview/{entity_name}/available-fields`) which returns the actual column set after all transformations. This ensures validation reflects the true state of the entity data, not just the static configuration.

The validation results are cached and automatically revalidated when:
- Specifications are added, edited, or deleted
- The project configuration changes
- The reconciliation view is refreshed

## Using the Reconciliation UI

### 1. Open the Reconciliation Tab

1. Open your project in the Shape Shifter web UI
2. Select the **Reconciliation** tab
3. On the **Configuration** tab, review the specifications list and the status column

### 2. Inspect a Specification

Each row shows:

- **Entity** and **Target Field**: the specification key
- **Remote Type**: the matched type, with its compatibility status
- **Mappings**: the number of recorded decisions
- **Thresholds**: the review and auto-accept values

### 3. Find Candidates

1. Select **Find Candidates** on the specification row.
2. The system fetches the configured source rows and queries the service for each encoded business key.
3. Progress is shown in a dialog. Rows with missing or duplicate keys, missing labels, or preparation errors are reported separately.
4. Matching proposes candidates only. It never accepts one.

### 4. Review Decisions

1. Open **Reconcile & Review**.
2. Filter rows by status.
3. Select a candidate, then select **Accept selected candidate**. Use **Reject** or **Local-only** when no candidate applies.
4. Use **Add Manual Link** when you already know the target ID.

### 5. Export to Mapping

1. Select **Export to Mapping**.
2. Accepted candidate URIs are checked against SEAD and copied into the mapping sidecar.
3. Review the reported per-key outcomes before continuing.

Decisions are stored in `<project>-reconciliation.yml`; applied links are stored in `<project>-mapping.yml`. Both files are preserved across sessions.

## Workflow Best Practices

### 1. Materialize Entities Before Reconciliation

**Best Practice**: Materialize dynamic entities (SQL/entity-derived) before reconciliation to ensure stable, consistent data.

**Why Materialize?**
- **Stability**: Frozen snapshot won't change during reconciliation
- **Performance**: No re-execution of complex queries
- **Versioning**: Captures data at specific point in time
- **Portability**: Data files can be shared/archived

**How to Materialize:**
1. Open entity in Entity Form Dialog
2. Ensure all dependencies are fixed or materialized
3. Click "Materialize" button
4. Choose storage format (Parquet recommended)
5. Entity is now type 'fixed' with frozen values

**Example:**
```yaml
# Before materialization (dynamic)
location:
  type: sql
  query: "SELECT * FROM locations WHERE active = true"
  data_source: project_db

# After materialization (frozen)
location:
  type: fixed
  columns: [location_id, location_name, country]
  values: "@file:materialized/location.parquet"
  materialized:
    enabled: true
    source_state:  # Original SQL config saved
      type: sql
      query: "SELECT * FROM locations WHERE active = true"
    materialized_at: "2026-01-29T12:00:00Z"
    materialized_by: "researcher@example.com"
```

See Entity Materialization Guide for full details.

### 2. Work Through Decisions

- Matching proposes candidates; a reviewer decides every row
- Review proposed rows and accept, reject, or mark them local-only
- Export to Mapping before expecting output to change
- Re-run candidate search after changing source data; decisions keyed by business key are preserved

### 3. Using Notes

Add notes to mappings for:
- **Manual decisions**: "Generic species, mapped to genus-level ID"
- **Uncertainty**: "Tentative match - verify with domain expert"
- **Data issues**: "Typo in source data: 'Qurcus' → Quercus"

### 4. Property Mapping Strategy

Map the properties the selected remote type actually serves. The manifest defines them; a type may serve none, in which case matching uses the search label alone.

Common patterns:

- **Sites**: coordinates (`latitude`, `longitude`), `country` or `place_name`, and `national_id` when available
- **Taxa**: `genus`, `family`, and `scientific_name` give the service more to compare
- **References**: structured identifiers (`doi`, `isbn`) discriminate best, with `year` and `authors` as support

Confirm the property names against the manifest before mapping them:

```bash
curl http://localhost:8000/reconcile | jq '.extend.property_settings'
```

### 5. Handling Unmatched Items

For items with no candidates or very low confidence:

1. **Check source data quality**: Verify spelling, formatting
2. **Add more properties**: Include additional property_mappings for better context
3. **Verify service type**: Ensure `service_type` appears in `reconciliation.supportedTypes` from `GET /reconcile`
4. **Manual research**: Look up correct SEAD ID in database
5. **Create new entities**: If entity doesn't exist in SEAD, coordinate with admins

## Catalog Examples

### Simple Specification (Using Entity Preview)

```yaml
entities:
  country:
    country_name:            # target field
      source: null           # use the entity's own rows
      remote:
        service_type: "country"
      mapping: []
```

### Using Another Entity's Data

The helper entity belongs to the project file. The catalog only references its name.

```yaml
# In the project file: a helper entity with extra fields
entities:
  taxon_enriched:
    source: taxa_lookup
    keys: ["species"]
    columns: ["species", "genus", "family", "author"]
```

```yaml
# In <project>-reconciliation.yml: match using the helper's rows
entities:
  taxon:
    species:                     # target field
      source: "taxon_enriched"   # read rows from the helper entity
      property_mappings:
        genus: genus
        family: family
        scientific_name: species
      remote:
        service_type: "taxon"
        columns: []
      mapping: []
```

### Custom SQL Query Source

```yaml
entities:
  site:
    site_name:                    # target field
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
      property_mappings:
        latitude: latitude
        longitude: longitude
        country: country
        national_id: national_id
        place_name: locality
      remote:
        service_type: "site"
        columns: []
      auto_accept_threshold: 0.95
      review_threshold: 0.70
      mapping: []
```

### Multi-Specification Example

A catalog can hold several entity and target field pairs, including several for one entity.

```yaml
entities:
  # Uses the entity's own rows
  country:
    country_name:
      source: null
      remote:
        service_type: "country"
        columns: []
      mapping: []

  # Reads rows from another entity
  taxon:
    species:
      source: "taxon_with_authors"
      property_mappings:
        genus: genus_col
        family: family_col
      remote:
        service_type: "taxon"
        columns: []
      mapping: []

  # Uses a custom query for full control over the input columns
  bibliographic_reference:
    citation:
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
      property_mappings:
        doi: doi
        title: title
        year: year
        authors: authors
      remote:
        service_type: "bibliographic_reference"
        columns: []
      auto_accept_threshold: 0.98
      mapping: []
```

## Troubleshooting

### Configuration Validation Errors

**Problem**: Red error icon appears in specifications list

**Solutions**:
1. **Hover over status icon** to see detailed validation messages
2. **Check entity exists**: Verify entity name in main project configuration
3. **Verify target_field**: Ensure target_field column exists after all transformations (check entity preview)
4. **Validate property mappings**: Confirm all source columns in property_mappings exist in the entity
5. **Consider column types**: Remember that columns can come from keys, columns, extra_columns, FK joins, or unnesting
6. **Use entity preview**: Open entity in Entity Editor to see final column list after all transformations

**Note**: The validation uses the **actual preview data API**, so it reflects the true state after filtering, linking, unnesting, and mapping operations. If a column is added through unnesting (var_name/value_name) or FK joins (local_keys), it will be properly validated.

### Service Connection Issues

**Problem**: Cannot connect to reconciliation service

**Solutions**:
- Verify the service answers: `curl http://localhost:8000/reconcile`
- Check `service_url` in the reconciliation catalog
- Confirm the backend can reach the service: `GET /api/v1/reconciliation/health`
- Ensure no firewall blocks the service port
- Check the service status chip in the Reconciliation tab; it shows the supported-type count when connected

### No Candidates Returned

**Problem**: Find Candidates returns no candidates

**Solutions**:
- **Check validation first**: a red alert blocks matching
- Verify `remote.service_type` appears in `reconciliation.supportedTypes` from `GET /reconcile`
- Confirm the selected source has rows
- Confirm the target field is populated in those rows
- Test the service directly with a sample query
- Verify property names in `property_mappings` appear in `extend.property_settings` for the selected type

### Low Confidence Scores

**Problem**: All matches have low confidence

**Solutions**:
- Add more property mappings to give the service more to compare
- Check for data quality issues (spelling, formatting, missing values)
- Use a target field whose values identify the record more precisely
- Widen the search with the alternative search dialog

### Decisions Not Persisting

**Problem**: Decisions lost after refresh

**Solutions**:
- Check the browser console and network tab for failed requests
- Check write permission on `data/projects/<project>/<project>-reconciliation.yml`
- Verify the backend is running (port 8012)
- Reload the project and confirm the decisions are listed again

## Advanced Project

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

### One Service per Project

Each catalog holds a single `service_url`, so a project matches against one reconciliation service. Specifications in the same catalog can still use different `remote.service_type` values when that service serves them.

```yaml
service_url: "http://localhost:8000"   # one service for the whole catalog
```

To match against a different service, use a different project. Do not add more `service_url` entries or `@include` directives to the same file.

## API Reference

All routes are under the `/api/v1` prefix. `{field}` is the target field name.

### Check Service Health

```
GET /api/v1/reconciliation/health
```

### Read the Service Manifest

```
GET /api/v1/reconciliation/manifest
```

Returns the supported types and the properties each type serves.

### Read or Replace the Catalog

```
GET /api/v1/projects/{project_name}/reconciliation
PUT /api/v1/projects/{project_name}/reconciliation/raw
```

### List Columns Available for Mappings

```
GET /api/v1/projects/{project_name}/reconciliation/available-fields/{entity_name}
```

Includes keys, columns, extra columns, FK join columns, and unnest columns.

### Read a Preview With Decisions Applied

```
GET /api/v1/projects/{project_name}/reconciliation/{entity_name}/{field}/preview
```

### Find Candidates

```
POST /api/v1/projects/{project_name}/reconciliation/{entity_name}/{field}/auto-reconcile
POST /api/v1/projects/{project_name}/reconciliation/{entity_name}/{field}/auto-reconcile-sync
```

The first form returns an `operation_id`; poll `GET /api/v1/operations/{operation_id}/progress` or stream `/stream`. Neither form accepts candidates.

### Record or Delete a Decision

```
POST   /api/v1/projects/{project_name}/reconciliation/{entity_name}/{field}/mapping
DELETE /api/v1/projects/{project_name}/reconciliation/{entity_name}/{field}/mapping
```

### Update a Specification

```
PUT /api/v1/projects/{project_name}/reconciliation/mapping-registry/{entity_name}/{field}
```

## See Also

- [Reconciliation Workflow](RECONCILIATION_WORKFLOW.md) - Finding candidates, reviewing decisions, and exporting links
- [Create a Reconciliation Specification](../USER_GUIDE.md#create-a-reconciliation-specification) - First-time setup steps
- [OpenRefine Reconciliation API Specification](https://reconciliation-api.github.io/specs/latest/)
- [CONFIGURATION_GUIDE.md](../CONFIGURATION_GUIDE.md) - Project and entity configuration reference
- [DEVELOPMENT.md](../DEVELOPMENT.md) - Development guide

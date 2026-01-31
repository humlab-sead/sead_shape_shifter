# Entity Materialization Feature

## Overview

The Entity Materialization feature allows users to freeze dynamic entities (SQL, entity-derived, or file-based) into fixed-value entities. This is essential for reconciliation workflows where entities need stable, versioned data that can be matched against external systems.

## Implementation Date

January 29, 2026

## Architecture

### Three-Layer Implementation

```
Frontend (Vue 3 + Vuetify)
    ↓
Backend API (FastAPI)
    ↓
Core Domain Logic (Pydantic Models)
```

## Core Components

### 1. Data Model (`src/model.py`)

#### MaterializationConfig
```python
class MaterializationConfig(BaseModel):
    enabled: bool = False
    source_state: dict[str, Any] | None = None  # Snapshot of original config
    materialized_at: str | None = None          # ISO timestamp
    materialized_by: str | None = None          # User email
    data_file: str | None = None                # Relative path to data file
```

#### TableConfig Extensions
- `materialized: MaterializationConfig` - Returns MaterializationConfig instance
- `is_materialized: bool` - Quick check property
- `can_materialize(project) -> tuple[bool, list[str]]` - Validation method

**Validation Rules:**
1. ✅ Entity must not be type 'fixed' (already frozen)
2. ✅ Entity must not already be materialized
3. ✅ All foreign key dependencies must be fixed or materialized
4. ✅ All source dependencies must be fixed or materialized

### 2. API Models (`backend/app/models/materialization.py`)

#### Request Models
- `MaterializeRequest`: storage_format (csv/parquet/inline), user_email
- `UnmaterializeRequest`: cascade (bool) - unmaterialize dependent entities

#### Response Models
- `MaterializationResult`: success, entity_name, rows_materialized, storage_file, errors
- `UnmaterializationResult`: success, unmaterialized_entities, requires_cascade, affected_entities
- `CanMaterializeResponse`: can_materialize, errors, estimated_rows

### 3. Service Layer (`backend/app/services/materialization_service.py`)

#### MaterializationService

**Methods:**
- `materialize_entity()` - Convert dynamic → fixed entity
- `unmaterialize_entity()` - Restore to dynamic state
- `_find_materialized_dependents()` - Helper for cascade detection

**Materialization Process:**
1. Validate entity can be materialized
2. Run ShapeShifter normalization pipeline
3. Extract DataFrame from table_store
4. Save to storage (parquet/csv/inline based on size and preference)
5. Snapshot current entity config to `source_state`
6. Update entity: type='fixed', add materialized section, set values
7. Save updated project

**Unmaterialization Process:**
1. Validate entity is materialized
2. Find dependent materialized entities
3. If cascade=True, unmaterialize dependents first (recursive)
4. Restore `source_state` configuration
5. Remove materialized section
6. Save updated project

### 4. API Endpoints (`backend/app/api/v1/endpoints/materialization.py`)

```
GET  /projects/{project_name}/entities/{entity_name}/can-materialize
POST /projects/{project_name}/entities/{entity_name}/materialize
POST /projects/{project_name}/entities/{entity_name}/unmaterialize
```

**Status Codes:**
- `200` - Success
- `400` - Validation error
- `404` - Entity not found
- `409` - Cascade required (unmaterialization)
- `500` - Server error

### 5. Validation (`src/specifications/entity.py`)

#### MaterializationSpecification
Auto-registered entity validator that checks:
- Materialized entities must have type='fixed'
- Must have either 'values' or 'data_file'
- Must have 'source_state' for unmaterialization
- Should have metadata fields (materialized_at, materialized_by)

### 6. Frontend Components

#### MaterializeDialog.vue
- Pre-validation check via `/can-materialize` endpoint
- Storage format selection (parquet/csv/inline)
- User email input (optional, for tracking)
- Error display if cannot materialize
- Estimated row count display

#### UnmaterializeDialog.vue
- Cascade warning if dependent entities exist
- Affected entities display
- Cascade checkbox to force unmaterialization
- Confirmation workflow

#### EntityFormDialog.vue Updates
- Added "Materialize" button for dynamic entities
- Added "Unmaterialize" button for materialized entities
- Buttons disabled during form editing
- Handlers reload entity list on success

#### EntityListCard.vue Updates
- Added materialization status chip
- Blue "Materialized" badge with database-check icon
- Displayed next to entity type chip

## Storage Strategy

### File-Based Storage
- **Location**: `projects/{project_name}/materialized/`
- **Parquet** (default): `{entity_name}.parquet` - Binary, efficient, recommended
- **CSV**: `{entity_name}.csv` - Human-readable, easy to edit externally
- **Path Format**: Relative to project root (`materialized/{entity}.parquet`)

### Inline Storage
- **Trigger**: Explicit storage_format='inline' OR row count < 1000
- **Format**: Values stored directly in YAML as list of lists
- **Use Case**: Small datasets, simple entities, version control friendly

## YAML Structure

### Materialized Entity Example
```yaml
entities:
  site:
    type: fixed                          # Always fixed after materialization
    public_id: site_id
    keys: [site_name]
    columns: [site_id, site_name, country_id, location_name]
    
    materialized:
      enabled: true
      source_state:                      # Original configuration
        type: sql
        data_source: project_db
        query: "SELECT * FROM sites"
        foreign_keys:
          - entity: country
            local_keys: [country_id]
            remote_keys: [country_id]
      materialized_at: "2026-01-29T14:30:00Z"
      materialized_by: "user@example.com"
      data_file: "materialized/site.parquet"
    
    values: "@file:materialized/site.parquet"  # External file reference
    
    foreign_keys:                        # FK preserved from original
      - entity: country
        local_keys: [country_id]
        remote_keys: [country_id]
```

### Inline Storage Example (Small Dataset)
```yaml
entities:
  sample_type:
    type: fixed
    public_id: sample_type_id
    keys: [type_name]
    columns: [sample_type_id, type_name, description]
    
    materialized:
      enabled: true
      source_state:
        type: entity
        source: sample_type_reference
      materialized_at: "2026-01-29T15:00:00Z"
      materialized_by: "user@example.com"
    
    values:                              # Inline values
      - [1, "Core", "Sediment core sample"]
      - [2, "Grab", "Surface grab sample"]
      - [3, "Thin Section", "Microscopy sample"]
```

## Use Cases

### 1. Reconciliation Preparation
**Problem**: Need stable entity data for matching against SEAD database  
**Solution**: Materialize entity → frozen values can be reconciled via mappings.yml

### 2. Performance Optimization
**Problem**: Complex SQL queries run slowly during pipeline execution  
**Solution**: Materialize once → subsequent runs use cached data

### 3. Data Versioning
**Problem**: External database changes break workflow  
**Solution**: Materialize → captures snapshot at specific point in time

### 4. Dependency Simplification
**Problem**: Entity depends on complex chain of other entities  
**Solution**: Materialize → breaks dependency chain, simplifies graph

### 5. Development/Testing
**Problem**: Need consistent test data across environments  
**Solution**: Materialize → portable data files in version control

## Workflow Examples

### Scenario 1: Prepare for Reconciliation
```
1. User has 'site' entity (type: sql)
2. Site depends on 'country' entity (type: fixed)
3. User clicks "Materialize" on site entity
4. System validates: ✓ Not fixed, ✓ Dependencies satisfied
5. System runs normalization → 150 rows
6. System saves to materialized/site.parquet
7. System updates YAML: type=fixed, adds materialized section
8. User can now add site mappings to mappings.yml
```

### Scenario 2: Cascade Unmaterialization
```
1. User has materialized chain: country → site → sample
2. User tries to unmaterialize 'site'
3. System detects 'sample' depends on 'site'
4. Dialog shows warning: "sample depends on this entity"
5. User checks "cascade" checkbox
6. System unmaterializes: sample → site (in order)
7. Both entities restored to original dynamic state
```

### Scenario 3: Storage Format Selection
```
Small entity (<1000 rows):
- Default: inline YAML
- User can override to parquet/csv

Large entity (>10,000 rows):
- Recommended: parquet (fastest, smallest)
- Alternative: csv (human-readable, editable)
- Not recommended: inline (YAML file too large)
```

## Dependencies

### Backend
- `pandas` - DataFrame operations
- `pyarrow` - Parquet file format
- `FastAPI` - REST API framework
- `Pydantic v2` - Data validation

### Frontend
- `Vue 3` - UI framework
- `Vuetify` - Component library
- `axios` - HTTP client

## Testing

### Backend Tests
```bash
# Test core validation
pytest tests/model/test_model.py::test_can_materialize

# Test service methods
pytest backend/tests/services/test_materialization_service.py

# Test API endpoints
pytest backend/tests/api/test_materialization_endpoints.py
```

### Frontend Tests
```bash
# Component tests
pnpm test:unit MaterializeDialog.spec.ts
pnpm test:unit UnmaterializeDialog.spec.ts
```

## Future Enhancements

### Planned Features
1. **Incremental Refresh**: Update materialized data without full re-materialization
2. **Scheduling**: Automatic re-materialization on schedule
3. **Diff Viewer**: Compare current vs. materialized state
4. **Version History**: Multiple snapshots with rollback support
5. **Selective Columns**: Materialize only subset of columns
6. **Row Filtering**: Materialize with custom filters applied

### Possible Improvements
- **Compression Options**: gzip, bz2, xz for parquet files
- **Partitioning**: Split large datasets across multiple files
- **Metadata Tags**: Custom tags for organizational purposes
- **Export Formats**: Additional formats (JSON, SQL dumps)
- **Audit Trail**: Track all materialization operations

## Migration Guide

### Existing Projects
No migration needed! The feature is opt-in:
1. Existing entities continue to work unchanged
2. No breaking changes to YAML format
3. Materialization adds new optional fields only

### Backward Compatibility
- Projects without materialized entities: No changes
- Projects with materialized entities: Fully supported
- Older versions reading new projects: Will ignore materialized section (graceful degradation)

## API Documentation

### Endpoint Details

#### Check if Entity Can Be Materialized
```http
GET /api/v1/projects/{project_name}/entities/{entity_name}/can-materialize
```

**Response:**
```json
{
  "can_materialize": true,
  "errors": [],
  "estimated_rows": 1500
}
```

#### Materialize Entity
```http
POST /api/v1/projects/{project_name}/entities/{entity_name}/materialize
Content-Type: application/json

{
  "storage_format": "parquet",
  "user_email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "entity_name": "site",
  "rows_materialized": 1500,
  "storage_file": "materialized/site.parquet",
  "storage_format": "parquet"
}
```

#### Unmaterialize Entity
```http
POST /api/v1/projects/{project_name}/entities/{entity_name}/unmaterialize
Content-Type: application/json

{
  "cascade": false
}
```

**Response (Success):**
```json
{
  "success": true,
  "entity_name": "site",
  "unmaterialized_entities": ["site"]
}
```

**Response (Cascade Required - 409):**
```json
{
  "detail": {
    "message": "Cannot unmaterialize: entities ['sample'] depend on this entity",
    "requires_cascade": true,
    "affected_entities": ["sample"]
  }
}
```

## Git Commit

This feature was implemented on branch `feat-materialize-entities` with the following commits:

```bash
feat(core): add MaterializationConfig to support entity freezing

- Add MaterializationConfig class with enabled, source_state, timestamps
- Add TableConfig.materialized and is_materialized properties
- Implement can_materialize() validation with dependency checking
- Validates: not fixed, not materialized, dependencies satisfied

BREAKING CHANGE: None (backward compatible, opt-in feature)
```

```bash
feat(backend): implement entity materialization service and API

- Create MaterializationService with materialize/unmaterialize methods
- Add API endpoints for materialization operations
- Implement cascade unmaterialization for dependent entities
- Support parquet, CSV, and inline storage formats
- Add MaterializationSpecification validator
```

```bash
feat(frontend): add materialization UI components

- Create MaterializeDialog with storage format selection
- Create UnmaterializeDialog with cascade warning
- Add materialize/unmaterialize buttons to EntityFormDialog
- Add materialization status chip to EntityListCard
- Show validation errors and estimated row counts
```

## Related Documentation

- [Three-Tier Identity System](/.github/copilot-instructions.md#three-tier-identity-system) - How materialized entities fit into identity architecture
- [Reconciliation Setup Guide](/docs/RECONCILIATION_SETUP_GUIDE.md) - Using materialized entities for reconciliation
- [Configuration Guide](/docs/CONFIGURATION_GUIDE.md) - YAML configuration reference
- [Backend API Reference](/docs/BACKEND_API.md) - API endpoint documentation

## Support

For issues or questions:
1. Check validation errors in MaterializeDialog
2. Review entity dependencies in can_materialize response
3. Verify storage paths are correct
4. Check backend logs for normalization errors

Common issues:
- **Cannot materialize**: Check dependencies are fixed/materialized
- **Cascade required**: Unmaterialize dependent entities first or use cascade
- **File not found**: Verify materialized/ directory exists
- **Validation errors**: Entity must be fully configured before materialization

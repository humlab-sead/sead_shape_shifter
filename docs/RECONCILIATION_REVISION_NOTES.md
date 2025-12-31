# Reconciliation Implementation - Service Manifest Integration

## Overview

The reconciliation feature has been revised to align with the OpenRefine Reconciliation API specification and the SEAD reconciliation service manifest. The implementation now uses service-defined entity types and property IDs for improved matching accuracy.

## Key Changes

### 1. Simplified ReconciliationRemote Model

**Before:**
```python
class ReconciliationRemote(BaseModel):
    data_source: str
    entity: str
    key: str
    service_type: str | None
    columns: list[str]
```

**After:**
```python
class ReconciliationRemote(BaseModel):
    service_type: str | None  # e.g., 'site', 'taxon'
```

**Rationale**: The remote configuration is now focused solely on reconciliation service integration. Other fields (data_source, entity, key) belong to Shape Shifter's linking configuration, not reconciliation.

### 2. Property Mappings

**Before:**
- `columns` field listed additional source columns
- Properties passed to service used column names directly

**After:**
- `property_mappings` maps service property IDs to source columns
- Example: `{"latitude": "lat_column", "genus": "genus_name"}`

**Rationale**: The reconciliation service defines specific property IDs (from `extend.property_settings` in manifest). We need to explicitly map our source columns to these IDs.

### 3. Service Type Validation

**Before:**
- Hardcoded `ENTITY_TYPE_MAPPING` dict in service
- Service types were capitalized (e.g., "Site", "Taxon")

**After:**
- Service types use lowercase IDs from manifest `defaultTypes`
- No hardcoded mapping - uses configured `service_type`
- `null` or empty `service_type` disables reconciliation

**Rationale**: Service types must match the IDs in the service manifest exactly.

### 4. Query Building

**Before:**
```python
# Build query from keys + columns
query_string = " ".join(keys + columns)

# Properties from columns
for col in entity_spec.columns:
    properties.append({"pid": col, "v": row[col]})
```

**After:**
```python
# Build query from keys only
query_string = " ".join(keys)

# Properties from property_mappings
for property_id, source_column in entity_spec.property_mappings.items():
    properties.append({"pid": property_id, "v": row[source_column]})
```

**Rationale**: Separates primary query text (keys) from contextual properties. Properties use service-defined IDs for proper matching.

## Project Format

### New YAML Structure

```yaml
service_url: "http://localhost:8000"

entities:
  site:
    keys:
      - site_name  # Used in query string
    
    property_mappings:
      # service_property_id: source_column_name
      latitude: lat
      longitude: lon
      country: country_name
      national_id: site_id
    
    remote:
      service_type: "site"  # From service defaultTypes
    
    auto_accept_threshold: 0.95
    review_threshold: 0.70
    
    mapping: []
```

## Available Service Types

From SEAD reconciliation service manifest (`/reconcile`):

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

## Available Properties

### Site Properties
- `latitude` - Geographic latitude (WGS84)
- `longitude` - Geographic longitude (WGS84)
- `country` - Country name
- `national_id` - National site identifier
- `place_name` - Geographic place/locality name

### Taxon Properties
- `scientific_name` - Full taxonomic name
- `genus` - Genus name
- `species` - Species name
- `family` - Family name

### Bibliographic Reference Properties
- `doi` - Digital Object Identifier
- `isbn` - International Standard Book Number
- `title` - Title of work
- `year` - Publication year
- `authors` - Authors
- `full_reference` - Full citation
- `bugs_reference` - BugsCEP reference

### Other Properties
- `method_abbreviation` - Method abbreviation (for methods)
- `dimension_abbreviation` - Dimension abbreviation (for dimensions)
- `description` - General description field

## Migration Guide

### Updating Existing Projects

**Old Format:**
```yaml
entities:
  taxon:
    keys: [species]
    columns: [genus, family]
    remote:
      data_source: "sead"
      entity: "tbl_taxa"
      key: "taxon_id"
      service_type: "Taxon"
    mapping: []
```

**New Format:**
```yaml
entities:
  taxon:
    keys: [species]
    property_mappings:
      genus: genus
      family: family
    remote:
      service_type: "taxon"  # Lowercase, from service manifest
    mapping: []
```

### Property Mapping Strategy

1. **Identify available properties** for your entity type from service manifest
2. **Map source columns** to service property IDs
3. **Prioritize structured identifiers** (IDs, codes) over text fields
4. **Add geographic properties** for spatial entities (latitude, longitude)
5. **Include hierarchical properties** for taxonomic entities (genus, family)

## Implementation Files Changed

### Backend
- `backend/app/models/reconciliation.py` - Updated models
- `backend/app/services/reconciliation_service.py` - Updated query building logic

### Frontend
- `frontend/src/types/reconciliation.ts` - Updated TypeScript types
- `frontend/src/components/reconciliation/ReconciliationView.vue` - Updated spec display
- `frontend/src/components/reconciliation/ReconciliationGrid.vue` - Updated column generation

### Documentation
- `docs/RECONCILIATION_SETUP_GUIDE.md` - Complete rewrite with new format
- `input/example-reconciliation.yml` - Example configuration with all entity types

## Testing Checklist

- [ ] Load existing reconciliation config and verify parsing
- [ ] Create new reconciliation config with property_mappings
- [ ] Run auto-reconcile and verify properties passed correctly
- [ ] Check service manifest integration (`GET /reconcile`)
- [ ] Verify service_type validation
- [ ] Test disabled reconciliation (service_type: null)
- [ ] Verify frontend displays property mappings correctly
- [ ] Test candidate review with different property combinations

## Next Steps

1. **Update existing configurations** to new format
2. **Test with SEAD reconciliation service** at http://localhost:8000
3. **Validate property IDs** against service manifest
4. **Fine-tune thresholds** based on matching performance
5. **Document custom properties** if service is extended
